-- Descrições das tabelas e colunas de `identity` e `metadata` (ADR 0022: toda tabela e coluna tem descrição).
-- Tabela nova em `ddl/` nasce com `COMMENT ON` na própria migração; um teste reprova tabela ou coluna sem descrição.

-- identity: a chave própria de pessoa
COMMENT ON TABLE identity.pessoa IS 'Pessoas do projeto, cada uma com uma chave própria e estável (nunca muda e nunca é reaproveitada). Uma linha por pessoa.';
COMMENT ON COLUMN identity.pessoa.id_pessoa IS 'Chave própria da pessoa no projeto, sem significado fora dele.';
COMMENT ON COLUMN identity.pessoa.created_at IS 'Instante (UTC, texto ISO 8601) em que a pessoa foi criada.';

COMMENT ON TABLE identity.pessoa_fusao IS 'Fusões de chaves: quando se descobre que duas chaves são a mesma pessoa, a mais nova é absorvida pela mais antiga e a fusão fica registrada aqui. Uma linha por fusão.';
COMMENT ON COLUMN identity.pessoa_fusao.id_pessoa_absorvida IS 'Chave que deixou de existir em identity.pessoa e nunca é reaproveitada.';
COMMENT ON COLUMN identity.pessoa_fusao.id_pessoa_sobrevivente IS 'Chave que ficou com os identificadores da absorvida.';
COMMENT ON COLUMN identity.pessoa_fusao.metodo IS 'Regra que mostrou que as duas chaves são a mesma pessoa.';
COMMENT ON COLUMN identity.pessoa_fusao.fundida_em IS 'Instante (UTC, texto ISO 8601) em que a fusão foi feita.';

COMMENT ON TABLE identity.pessoa_identificador IS 'Identificadores de cada pessoa nas fontes oficiais (tabela-ponte): liga o registro da fonte à chave própria. Uma linha por identificador.';
COMMENT ON COLUMN identity.pessoa_identificador.source IS 'Fonte do identificador (por exemplo, camara, senado, tse).';
COMMENT ON COLUMN identity.pessoa_identificador.id_type IS 'Tipo do identificador na fonte (por exemplo, deputado, senador, candidato).';
COMMENT ON COLUMN identity.pessoa_identificador.source_id IS 'Valor do identificador na fonte.';
COMMENT ON COLUMN identity.pessoa_identificador.id_pessoa IS 'Chave própria da pessoa a que o identificador pertence.';
COMMENT ON COLUMN identity.pessoa_identificador.method IS 'Como o vínculo foi feito: identificador oficial da própria fonte, regra de nome civil e nascimento, ou vínculo aprovado por uma pessoa.';
COMMENT ON COLUMN identity.pessoa_identificador.confirmed_by IS 'Quem aprovou o vínculo, quando ele foi aprovado à mão.';
COMMENT ON COLUMN identity.pessoa_identificador.linked_at IS 'Instante (UTC, texto ISO 8601) em que o vínculo foi feito.';

-- metadata: operação da pipeline
COMMENT ON TABLE metadata.migrations IS 'Migrações de `ddl/` já aplicadas neste warehouse. Uma linha por migração.';
COMMENT ON COLUMN metadata.migrations.version IS 'Número da migração (por exemplo, 0006).';
COMMENT ON COLUMN metadata.migrations.applied_at IS 'Instante (UTC, texto ISO 8601) em que a migração foi aplicada.';

COMMENT ON TABLE metadata.runs IS 'Execuções de cada etapa da pipeline (extração, carga, transformação), com contagem de linhas e resultado. Uma linha por execução.';
COMMENT ON COLUMN metadata.runs.id IS 'Identificador da execução.';
COMMENT ON COLUMN metadata.runs.stage IS 'Etapa executada (extract, load, transform_pre, transform_post, freshness...).';
COMMENT ON COLUMN metadata.runs.source IS 'Fonte processada, quando a etapa é de uma fonte.';
COMMENT ON COLUMN metadata.runs.dataset IS 'Dataset processado, quando a etapa é de um dataset.';
COMMENT ON COLUMN metadata.runs.year IS 'Partição processada (ano, mês AAAAMM ou legislatura), quando houver.';
COMMENT ON COLUMN metadata.runs.started_at IS 'Instante (UTC, texto ISO 8601) em que a execução começou.';
COMMENT ON COLUMN metadata.runs.finished_at IS 'Instante (UTC, texto ISO 8601) em que a execução terminou.';
COMMENT ON COLUMN metadata.runs.code_version IS 'Versão do código que fez a execução.';
COMMENT ON COLUMN metadata.runs.rows_in IS 'Linhas lidas pela etapa.';
COMMENT ON COLUMN metadata.runs.rows_out IS 'Linhas gravadas pela etapa.';
COMMENT ON COLUMN metadata.runs.status IS 'Resultado da execução (ok ou error).';
COMMENT ON COLUMN metadata.runs.message IS 'Mensagem de erro, quando a execução falhou.';

COMMENT ON TABLE metadata.captures IS 'Cada arquivo capturado da fonte e guardado no landing, com hash, endereço e data. É a prova do que a fonte entregou. Uma linha por arquivo.';
COMMENT ON COLUMN metadata.captures.id IS 'Identificador da captura; as tabelas do raw o guardam como _source_file_id.';
COMMENT ON COLUMN metadata.captures.source IS 'Fonte do arquivo.';
COMMENT ON COLUMN metadata.captures.dataset IS 'Dataset do arquivo.';
COMMENT ON COLUMN metadata.captures.year IS 'Partição do arquivo (ano, mês AAAAMM ou legislatura); vazio nos datasets sem partição.';
COMMENT ON COLUMN metadata.captures.url IS 'Endereço oficial de onde o arquivo foi baixado.';
COMMENT ON COLUMN metadata.captures.sha256 IS 'Impressão digital (SHA-256) do arquivo: prova que o arquivo guardado é o que a fonte entregou.';
COMMENT ON COLUMN metadata.captures.size_bytes IS 'Tamanho do arquivo em bytes.';
COMMENT ON COLUMN metadata.captures.path IS 'Caminho do arquivo no landing, a partir da pasta de armazenamento.';
COMMENT ON COLUMN metadata.captures.captured_at IS 'Instante (UTC, texto ISO 8601) da primeira captura deste conteúdo.';
COMMENT ON COLUMN metadata.captures.last_checked_at IS 'Instante (UTC, texto ISO 8601) da última vez que a fonte foi consultada e o conteúdo continuava o mesmo.';
COMMENT ON COLUMN metadata.captures.run_id IS 'Execução (metadata.runs.id) que fez a captura.';
COMMENT ON COLUMN metadata.captures.etag IS 'ETag que a fonte informou na captura, quando informou.';
COMMENT ON COLUMN metadata.captures.last_modified IS 'Cabeçalho Last-Modified que a fonte informou na captura, quando informou.';
COMMENT ON COLUMN metadata.captures.loaded_at IS 'Instante (UTC, texto ISO 8601) em que o arquivo foi carregado no raw; vazio se ainda não foi.';

COMMENT ON TABLE metadata.capture_items IS 'Itens buscados um a um nos datasets por item (tramitação, processos...), com o arquivo de lote em que cada resposta foi guardada. Uma linha por item buscado.';
COMMENT ON COLUMN metadata.capture_items.id IS 'Identificador da linha.';
COMMENT ON COLUMN metadata.capture_items.capture_id IS 'Captura (metadata.captures.id) do lote que guardou a resposta do item.';
COMMENT ON COLUMN metadata.capture_items.source IS 'Fonte do item.';
COMMENT ON COLUMN metadata.capture_items.dataset IS 'Dataset do item.';
COMMENT ON COLUMN metadata.capture_items.item IS 'Identificador do item na fonte (por exemplo, o código da proposição).';
COMMENT ON COLUMN metadata.capture_items.url IS 'Endereço oficial consultado para este item.';
COMMENT ON COLUMN metadata.capture_items.status IS 'Código HTTP da resposta (0 quando a fonte não respondeu).';
COMMENT ON COLUMN metadata.capture_items.sha256 IS 'Impressão digital (SHA-256) da resposta do item.';
COMMENT ON COLUMN metadata.capture_items.fetched_at IS 'Instante (UTC, texto ISO 8601) em que o item foi buscado.';
COMMENT ON COLUMN metadata.capture_items.version IS 'Versão do item na fonte (por exemplo, data da última atualização), usada para saber se ele mudou.';

COMMENT ON TABLE metadata.source_checks IS 'Resultado das verificações das fontes e das cargas: disponibilidade, cabeçalho, volume e balanço de cada carga. Uma linha por verificação.';
COMMENT ON COLUMN metadata.source_checks.id IS 'Identificador da verificação.';
COMMENT ON COLUMN metadata.source_checks.checked_at IS 'Instante (UTC, texto ISO 8601) da verificação.';
COMMENT ON COLUMN metadata.source_checks.source IS 'Fonte verificada.';
COMMENT ON COLUMN metadata.source_checks.dataset IS 'Dataset verificado.';
COMMENT ON COLUMN metadata.source_checks.partition IS 'Partição verificada (ano, mês AAAAMM ou legislatura), quando houver.';
COMMENT ON COLUMN metadata.source_checks.check_name IS 'Nome da verificação (availability, schema, volume, carga, linhas_removidas...).';
COMMENT ON COLUMN metadata.source_checks.status IS 'Resultado: ok, warn (aviso) ou error (erro).';
COMMENT ON COLUMN metadata.source_checks.detail IS 'Detalhe do resultado (contagens, colunas que mudaram, mensagem de erro).';

COMMENT ON TABLE metadata.dbt_results IS 'Resultado de cada modelo, teste e verificação de frescor do dbt em cada execução. Uma linha por nó e execução.';
COMMENT ON COLUMN metadata.dbt_results.run_id IS 'Execução (metadata.runs.id) que rodou o dbt.';
COMMENT ON COLUMN metadata.dbt_results.unique_id IS 'Identificador do nó no dbt (por exemplo, test.dado_publico_brasil.nome_do_teste).';
COMMENT ON COLUMN metadata.dbt_results.kind IS 'Tipo do nó: model, test ou freshness.';
COMMENT ON COLUMN metadata.dbt_results.status IS 'Resultado: success, pass, warn, fail ou error.';
COMMENT ON COLUMN metadata.dbt_results.failures IS 'Linhas que fizeram o teste falhar ou avisar.';
COMMENT ON COLUMN metadata.dbt_results.message IS 'Mensagem do dbt para o nó.';
COMMENT ON COLUMN metadata.dbt_results.recorded_at IS 'Instante (UTC, texto ISO 8601) em que o resultado foi gravado.';
