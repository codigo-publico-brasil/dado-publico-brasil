# ADR 0036: R2 privado como fonte da verdade da identidade e do metadata; disco local descartável

- **Status:** proposto (2026-11-02)
- **Data:** 2026-11-02
- **Complementa:** [ADR 0035](0035-lakehouse-publico-no-r2.md) (item 7: o bucket privado) e [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (item 4: cópia imutável da identidade no armazenamento de objetos, com teste de restauração).
- **Para quem é:** quem opera ou implementa a plataforma. Responde: o que precisa sobreviver à perda da máquina, onde fica e como se recupera.

## Contexto

Requisito do fundador: nada importante pode ficar só no disco local; ele é efêmero, só para temporários. Hoje tudo está em `data_store/`: warehouse (11 GB, reconstruível do landing em cerca de 6 h, quase tudo na carga do dlt, issue 154; o dbt e a identidade levam cerca de 20 min), landing (16 GB, 990 arquivos, o maior com 0,64 GB), fotos (1 GB, 50 mil arquivos extraídos dos pacotes do landing), snapshots da identidade (41 MB), o estado do dlt, do dbt e do Dagster, e o `metadata` (capturas com hash, execuções, testes), que só existe dentro do warehouse (issue 153).

Dois defeitos concretos hoje: perder o disco perde a identidade (a chave `id_pessoa`, que não pode mudar) e o registro das capturas; e `core/rebuild.py` recria a identidade com chaves novas, contra o ADR 0014.

Decisão do fundador nesta rodada: o **landing e as fotos continuam só no disco local**, para poupar custo e tempo.

## Decisão

1. **Fonte da verdade de cada coisa:**

   | O quê | Fonte da verdade | Na máquina |
   | --- | --- | --- |
   | identidade (`identity.*`) | snapshots Parquet no bucket privado, `snapshots/identity/<AAAAMMDDTHHMMSS>/` | cópia de trabalho no warehouse |
   | `metadata` (as 5 tabelas de `rebuild.TABLES`) | `metadata/<tabela>.parquet` no bucket privado | cópia de trabalho no warehouse |
   | landing e fotos | **disco local** (risco aceito, item 7) | idem |
   | warehouse (raw a marts) | reconstruído do landing | cache descartável |
   | estado do dlt, do dbt e do Dagster | nenhum: descartável | temporário |

   O estado das ferramentas não precisa de cópia: o do dlt só vale para o warehouse que o criou (a reconstrução já o põe de lado), o do dbt é gerado a cada `build`, e o histórico de execuções que importa está em `metadata.execucoes`. Perder o `DAGSTER_HOME` só obriga a primeira rodada depois da restauração a ser manual (`processar_tudo`).

2. **Escrita (push), sempre pelo `COPY` do DuckDB direto no `r2://`**, como o export do ADR 0035; sem cópia local nem dependência nova:
   - **identidade:** `snapshot.take` grava a pasta nova no bucket privado e, por último, um marcador `_concluido`; pasta sem marcador é ignorada. Roda dentro de `build.resolve_identity`, antes da fase 2 do dbt: se o envio falhar, a execução para, e nenhuma chave nova chega aos marts, ao lake público ou ao PostgreSQL sem cópia.
   - **metadata:** cada tabela é regravada inteira (um PUT é atômico) ao fim de `landing.extract_plan` (por fonte) e de `build.run`. **Trava contra apagar:** recusa enviar se o `metadata.capturas` remoto tem mais linhas que o local (capturas só crescem); isso impede que uma máquina nova, sem restaurar, sobrescreva a verdade.
3. **Leitura (pull) numa máquina vazia:** ao criar um warehouse novo (arquivo inexistente) com o bucket privado configurado, `migrations.open_warehouse` restaura o `metadata` e o snapshot mais recente da identidade, avança as sequências além do maior id e marca `dt_carga` nulo. A reconstrução (`rebuild`) passa a partir daí, sem exigir o warehouse antigo, e a identidade **mantém as chaves**.
4. **Um único escritor por credencial, não por código:** só a máquina de produção tem `DADO_PUBLICO_R2_BUCKET_PRIVADO` e um token com escrita no bucket privado. Sem a variável, tudo fica local como hoje (desenvolvimento). Duas máquinas escrevendo gerariam `id_pessoa` em conflito; a trava do item 2 é a segunda barreira.
5. **Idempotência:** snapshot só se grava quando a identidade muda (já é assim) e nunca sobrescreve; o metadata regravado com o mesmo conteúdo não muda nada.
6. **Bucket privado nunca público:** sem domínio nem `r2.dev`. Mesmo token do lake público (ADR 0035).
7. **Risco aceito: o landing só no disco.** Perdida a máquina, identidade e metadata voltam, mas o raw precisa **recapturar das fontes oficiais** (`run --historical`). Para isso o `extract` trata como mudada a captura cujo arquivo local sumiu: baixa de novo e, se o hash é o mesmo, devolve o arquivo ao `caminho` original (o registro continua verdadeiro); se o hash difere, vira captura nova. Arquivos que a fonte mudou ou tirou do ar **não se recuperam**: ficam no metadata com o hash e `dado-publico verify` os aponta como ausentes. Os lotes dos datasets por item (`foreach`) não se refazem iguais.
8. **Ponto de extensão para o landing (gatilho: perda de arquivo, fonte que some, ou decisão de custo):** a mesma regra serve sem retrabalho. Chave no bucket = `metadata.capturas.caminho`; envio antes de `register_capture` (a linha nunca aponta para arquivo sem cópia), com `If-None-Match: *` (imutável) e `x-amz-checksum-sha256` (o R2 confere o hash); leitura sob demanda por uma função `landing.local_file(settings, captura)`, que baixa se faltar e confere o SHA-256, usada onde hoje se lê `storage_root / caminho` (`loader`, `photos`, `foreach.verify`). Basta o signer SigV4 de `export.r2_request`, movido para `core` e com GET: o maior arquivo tem 0,64 GB, abaixo do limite de 5 GB de um PUT; falha reenvia o arquivo inteiro. Arquivo acima de ~4 GB é o gatilho de um ADR para multipart (`boto3` ou código próprio). As fotos seguem derivadas do landing (`photos.extract_all`), sem cópia própria.

## Alternativas consideradas

- **Copiar o warehouse (11 GB) para o R2:** recuperaria em minutos, mas passa de 5 GB (multipart, dependência nova) e exige o arquivo fechado. A reconstrução é o caminho; se 6 h pesar, a resposta é a issue 154 (carga em Parquet), não a cópia.
- **Landing no R2 já agora:** tira o maior risco (fonte que some), por cerca de US$ 0,25 por mês e uma carga inicial de 16 GB; adiado pelo fundador (item 8).
- **DuckLake ou um DuckDB separado para identidade e metadata:** tira o estado do disco, mas sem chave primária e com estrutura nova (ADR 0034).
- **`rclone` ou `aws s3 sync` na operação:** sem código, mas sem ordem garantida (estado novo antes da cópia) nem trava contra sobrescrever.
- **Trava distribuída (objeto de concessão no R2):** garante escritor único por código; mais código que a regra de credencial resolve.
- **Estado do Dagster no PostgreSQL de serviço:** histórico durável, mas dependência nova (`dagster-postgres`) para dado que o `metadata` já guarda.

## Consequências

- Custo quase nulo: snapshots e metadata somam dezenas de MB, dentro dos 10 GB gratuitos. Com o landing (item 8), cerca de 17 GB a US$ 0,015 por GB-mês, e cresce sem limite, porque o landing não se apaga.
- A reconstrução numa máquina vazia não depende mais do warehouse antigo e preserva `id_pessoa`; o `rebuild --old-warehouse` continua para quem tem o arquivo.
- Uma máquina nova sem o landing leva horas recapturando e pode perder versões que as fontes não publicam mais (risco aceito, item 7). A reconstrução reflete só a captura vigente de cada URL; o acumulado dos datasets `merge` não volta (issue 155).
- Novo módulo pequeno em `core` (raiz privada, segredo, envio e restauração); `export` passa a usar o segredo e o signer de lá.
- Teste de restauração no CI com o bucket substituído por uma pasta temporária, e teste de integração opcional contra um prefixo isolado do bucket real.
