# ADR 0012: Dataset por item (`foreach`), lotes com envelope e auditoria

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Complementa:** [ADR 0011](0011-buscar-ler-custom-e-chave-por-fonte.md) (buscar, guardar, ler).

## Contexto

Tramitação, autoria e situação atual das proposições só existem por item: uma chamada à API para cada proposição (Câmara) ou processo (Senado). A captura só sabia pedir uma janela (um ano, uma legislatura). O fundador pediu que a plataforma seja completa, auditável e de qualidade, e que a carga total só rode quando ele solicitar, com amostras dos itens mais recentes enquanto isso.

## Decisão

1. **`load: foreach` no YAML.** Os itens saem do raw de outro dataset da mesma fonte (`foreach.from`), com `where` opcional. `{item}` vai na URL. `recent_by` ordena do mais recente ao mais antigo (amostras e cargas limitadas começam pelo que mais importa). Cada dataset pode ter `format` e `headers` próprios (a API em JSON convive com os arquivos em CSV da mesma fonte).
2. **Só roda quando pedido:** `--foreach N` busca os N itens mais recentes que faltam por dataset; `--foreach all` busca todos. Sem a opção, os datasets por item ficam de fora dos planos normais.
3. **Landing em lotes com envelope.** Cada lote é um `.jsonl.gz` (até `batch_size` itens) em que cada linha é `{item, url, status, buscado_em, sha256, corpo}`; o `corpo` é a resposta byte a byte (em base64 se não for UTF-8) e o gzip é determinístico. O lote entra em `metadata.captures` como qualquer captura, e **`metadata.capture_items`** indexa cada item (lote, URL, status, hash do corpo, versão e data). O raw lê só as respostas 200 e acrescenta a coluna `_item`.
4. **Retomável e idempotente:** cada lote é gravado e registrado ao terminar; uma execução interrompida continua do próximo. Item novo, item cuja `version` (coluna do dataset de origem) mudou, item com falha (5xx ou sem resposta) e item mais velho que `refresh_after_days` são buscados de novo; resposta 404 não é repetida enquanto a versão não mudar.
5. **Educação com a fonte:** `access.rate_limit` (padrão 4 chamadas por segundo), identificação no `User-Agent` e nova tentativa só em 5xx e falha de rede. A Câmara informa que a API serve para consultas selecionadas, "um pouco de cada vez", e os arquivos em lote para conjuntos grandes; por isso a API só é usada onde não há arquivo.
6. **Auditoria e qualidade:**
   - `dado-publico verify` confere o hash de cada arquivo do landing, o de cada resposta dentro dos lotes e o índice `capture_items`;
   - `dado-publico coverage` mostra, por dataset, itens esperados, obtidos, inexistentes (404), com falha e faltantes; a cobertura também é gravada em `metadata.source_checks`;
   - testes do dbt medem as lacunas (proposições-alvo sem tramitação) e conferem o staging contra os marts.

## Termos de uso verificados (21/10/2026)

- **Câmara** (FAQ dos dados abertos): acesso gratuito, sem cadastro, "sem restrição" a uso comercial, sem limite de requisições informado e sem licença formal; dados pessoais de parlamentares e colaboradores ficam de fora (Ato da Mesa 45/2012). A API é indicada para consultas pontuais.
- **Senado:** os dados são "disponibilizados sob licença que permita sua livre utilização", sem nomear a licença; a "Política de uso do portal" não pôde ser lida. Sem cadastro e sem limite de requisições informado.
- Conclusão: o uso é permitido e gratuito; como nenhum limite é publicado, a plataforma mantém uma taxa conservadora e identificada. A licença formal continua a confirmar.

## Escopo desta entrega

- **Câmara:** tramitação das proposições que podem virar norma (PL, PLP, PEC, MPV, PDL, PLV, PLN e PRC), mart `tramitacoes`.
- **Senado:** processo de cada matéria votada: situação atual (preenche `proposicoes.situacao`) e a norma gerada (`normas_geradas`). A autoria vem no raw (`processos__autoria_iniciativa`) e o corpo completo, no landing; tramitação do Senado e autoria nos marts ficam para depois.
- Carga real em amostra dos itens mais recentes; a carga total, quando o fundador pedir.

## Consequências

- Uma fonte nova que precise de uma chamada por item entra só em YAML, com a mesma auditoria.
- O landing de itens cresce com a carga total (estimativa: dezenas de milhares de proposições, em lotes compactados); por isso a carga total é decisão do fundador.
