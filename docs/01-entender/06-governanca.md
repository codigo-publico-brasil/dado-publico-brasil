# Governança, segurança, qualidade e frescor dos dados

Como o projeto garante que o dado é confiável, seguro e fácil de manter. Cada seção diz o que a prática significa, como está implementada hoje e o que ainda falta. Também serve de roteiro de estudo: os quadros **Conceito** ligam a prática ao vocabulário de governança de dados corporativa (DAMA-DMBOK).

## 1. Catálogo e dono dos dados

Cada tabela de cada camada é descrita **onde nasce**: o raw nas fontes do dbt (`_<fonte>__sources.yml`) e no contrato `sources/<poder>/<esfera>/<fonte>.yml`; staging, intermediate e marts no YAML do modelo; `identity` e `metadata` nas fontes internas do dbt. Descrição, sensibilidade (`meta.sensitivity`), grain e dono vivem no `meta`. O [catálogo de dados](../03-consultar/01-catalogo.md) é **gerado** do manifesto do dbt (`uv run dado-publico catalog`), sem lista paralela. Um teste confere que o catálogo cobre as tabelas do pipeline (e que toda descrição está preenchida) e outro que `docs/03-consultar/01-catalogo.md` está em dia.

> **Conceito: catálogo de dados e dono (*data owner / steward*).** Dado sem dono e sem descrição vira dado que ninguém ousa mudar nem apagar. O catálogo responde "o que é isto, de onde vem, quem responde por isso". Aqui o dono é o fundador; com o tempo, cada fonte teria um responsável.

## 2. Classificação de sensibilidade

| Classe | Significado | Exemplo |
| --- | --- | --- |
| `publico` | dado público sem dado pessoal | proposição, votação, partido |
| `publico-agente-publico` | dado público sobre agente público no exercício da função | nome, foto, redes sociais, data de nascimento de deputado |
| `publico-dados-pessoais-de-terceiros` | dado que a fonte publica e que inclui pessoas que não são agentes públicos (cidadão comum) | favorecidos de emendas (nome e CPF mascarado de pessoa física) |
| `controle` | metadado operacional | registro de execuções |

**Sinalização em três níveis.** A classe vale para a tabela (`meta.sensitivity`); a coluna que identifica uma pessoa leva `meta: {pii: true}` e aparece marcada no dicionário do [catálogo](../03-consultar/01-catalogo.md); e, nas tabelas que misturam pessoas jurídicas e físicas, uma coluna por linha (`fl_contem_dado_pessoal`) deixa a aplicação decidir como mostrar. A plataforma guarda o que a fonte publica; quem consome decide a exibição. Um teste confere que a classe é uma das acima e que tabela com coluna `pii` não é `publico`.

Regras (princípio IX da constituição do projeto):

- Dado público de agente público é permitido, **com fonte e data de captura**.
- **Documentos pessoais (CPF, RG, título de eleitor) nunca entram em nenhuma camada.** O CPF existe no arquivo da Câmara, mas a padronização não o lê. Um teste confere que nenhuma tabela tem coluna desse tipo, e outro confere que o valor do CPF de teste não aparece no banco.
- **Nenhuma página sobre pessoa privada.**

> **Conceito: minimização de dados (LGPD, art. 6º).** Coletar só o necessário para a finalidade. A forma mais segura de proteger um dado é nunca guardá-lo. Dado público de agente público tem base legal própria (tratamento de dados tornados públicos), mas continua exigindo finalidade e proporcionalidade.

## 3. Qualidade: acurácia, completude, consistência

Os testes são do **dbt**: genéricos (`unique`, `not_null`, `relationships`) no YAML dos modelos, e singulares em `dbt/tests/` (`reconciliation/` com severidade `error`, `gaps/` com `warn`). Rodam junto com a transformação e **bloqueiam a publicação** se falharem (o `dbt build` não segue para as tabelas que dependem de um teste reprovado). As lacunas conhecidas da fonte são testes `warn`: a contagem de linhas que falharam mede o tamanho da lacuna. O resultado de cada execução é gravado em `metadata.dbt_results` e aparece na página de qualidade da aplicação. Os marts têm ainda **contrato de colunas e tipos**.

| Dimensão | Pergunta | Exemplo de teste |
| --- | --- | --- |
| Integridade | Toda referência aponta para algo que existe? | `voto_sem_pessoa`, `identificador_sem_pessoa` |
| Completude | O que está faltando? | `proposicao_sem_situacao`, `pessoa_sem_foto` |
| Consistência entre camadas | Alguma linha se perdeu no caminho? | `votos_perdidos_do_staging_aos_marts` |
| Padronização | A regra de caixa pegou tudo? | `nome_de_pessoa_ainda_em_maiusculas` |
| Acurácia (reconciliação) | Os números batem com os totais da própria fonte? | `votacao_com_total_sim_diferente_dos_votos` |

Dois tipos de teste:

- **`erro`:** deve dar zero. Se não der, há defeito no pipeline e a camada seguinte não deveria ser publicada.
- **`medida`:** informa o estado dos dados sem reprovar. Lacunas esperadas aparecem aqui, como autorias de proposições de anos ainda não carregados, ou votações simbólicas, que por natureza não têm voto individual.

> **Conceito: reconciliação.** Comparar o que construímos com um total que a fonte publica por outro caminho. A Câmara publica o total de votos Sim/Não de cada votação; se a soma dos votos individuais não bate, ou o dado está incompleto, ou o nosso pipeline perdeu algo, ou a votação foi simbólica. O teste separa os casos em vez de esconder a diferença.

> **Conceito: acurácia não é a mesma coisa que fidelidade à fonte.** O pipeline garante que o dado é fiel ao arquivo oficial. Se o arquivo estiver errado, o dado fiel estará errado. Já foi observado um caso: a data de falecimento de um deputado consta no arquivo em lote mas não na API de detalhe. As divergências entre fontes oficiais são registradas, não "corrigidas" por escolha própria.

O que ainda falta: comparar uma amostra com as páginas oficiais da Câmara, o que exige conferência humana periódica; hoje a validação foi feita contra a API (autores, votos e pessoas, em amostra).

## 4. Frescor

Cada captura guarda `data_captura` (primeira vez que aquele conteúdo foi visto) e `ultima_verificacao` (última vez em que a fonte foi consultada e entregou o mesmo conteúdo). A diferença entre agora e `ultima_verificacao` é o **atraso**, mostrado na página de qualidade do explorador. O catálogo declara o frescor esperado de cada tabela (a Câmara atualiza os arquivos em lote diariamente).

> **Conceito: frescor (*freshness*) como contrato.** "Dado atualizado" só significa algo se houver um limite combinado e uma medição. Quando houver agendamento, um atraso acima do esperado vira alerta.

O que ainda falta: o agendamento. As etapas já são idempotentes e registram execução, que é o pré-requisito; falta ligá-las ao Dagster (ADR 0002) e definir os alertas.

## 5. Linhagem e auditoria

Toda linha aponta para a captura de origem (`id_captura`), e toda captura aponta para a execução que a trouxe. Toda execução registra versão do código, linhas lidas e gravadas e resultado. Nos datasets por item, a captura também aponta para cada resposta (`metadata.capture_items`: status HTTP e hash do corpo), e `dado-publico verify` confere os hashes de todo o landing. O passo a passo de como provar a origem de um dado está em [auditoria](../02-fazer/05-auditar.md); mais detalhes em [camadas](03-camadas.md).

## 6. Segurança

| Prática | Estado |
| --- | --- |
| Nenhum segredo, chave ou dado pessoal no repositório (`gitleaks` na esteira) | ativo |
| Dados fora do git (`data_store/` ignorado) | ativo |
| A aplicação abre o warehouse só para leitura e lê só os marts (e `metadata`, para a página de qualidade); não importa o código da camada de dados | ativo e testado |
| Servidor do explorador escuta só em `127.0.0.1` | ativo |
| Texto exibido sempre escapado contra injeção de HTML | ativo, com teste |
| Poucas dependências (a camada de dados usa só a biblioteca padrão do Python) | ativo |
| Permissão por esquema no banco (usuário da aplicação só em `marts`) | previsto para o PostgreSQL do piloto |
| Download com identificação (`User-Agent`) e sem credencial | ativo; sem limite de taxa conhecido, ver [fontes](../03-consultar/03-fontes-de-dados.md) |

> **Conceito: privilégio mínimo.** Cada componente recebe só o acesso de que precisa. A aplicação não precisa ler o raw nem escrever em nada; por isso não terá permissão para isso.

## 7. Manutenção

- **Código e testes juntos:** cada etapa tem testes com dados sintéticos; nenhum teste usa a rede.
- **Reprodutibilidade:** as camadas derivadas podem ser apagadas e refeitas do landing.
- **Mudança de formato da fonte:** o landing guarda o arquivo antigo; o `dbt build` quebra se uma coluna esperada sumir do raw. Falta o teste de contrato contra respostas reais gravadas.
- **Decisões registradas** em ADR; mudanças aceitas viram ADR novo.

## 8. Texto reescrito por IA (proposta, ainda não implementada)

Ementas às vezes são difíceis de entender. Um resumo em linguagem simples gerado por IA é útil, mas é **conteúdo derivado**, não dado oficial. Condições para existir:

1. Campo separado, rotulado "resumo gerado por IA", com modelo, versão e data. A ementa oficial aparece sempre ao lado.
2. O texto só pode conter o que está na ementa: sem opinião, sem linguagem avaliativa, sem informação nova.
3. Uma pessoa revisa uma amostra antes de qualquer exibição pública, e o resultado da revisão é registrado.
4. Precisa de spec e ADR próprios (custo, modelo, política de revisão).

## Resumo do estado

| Pilar | Estado hoje | Próximo passo |
| --- | --- | --- |
| Catálogo | feito, com teste | publicar o catálogo como página |
| Sensibilidade | feita, com testes | revisão por pessoa a cada fonte nova |
| Qualidade | testes de erro e de medida | contrato com respostas gravadas; amostra contra páginas oficiais |
| Frescor | medido por captura | agendar e alertar |
| Linhagem | completa até o arquivo do landing e, nos datasets por item, até a resposta de cada item (`verify` confere) | exibir a linhagem na página |
| Segurança | leitura somente, segredos varridos | permissão por esquema no PostgreSQL |
