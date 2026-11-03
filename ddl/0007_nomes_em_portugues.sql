-- Padroniza `metadata` e `identity` à convenção de nomes (ADR 0022): nomes em português com o tema na frente,
-- prefixos id_/dt_, instantes em TIMESTAMP (UTC) e descrição de toda tabela e coluna. Muda só nomes e tipos: nenhuma
-- linha é perdida. Roda uma vez (a tabela de migrações registra), na transação que `migrations.apply` abre por arquivo: renomeações, descrições e registro entram juntos ou nenhum.
-- As sequências não se renomeiam no DuckDB: cria-se a nova, avança-se até o maior id e troca-se o padrão da coluna.
-- metadata.migrations -> metadata.migracoes
ALTER TABLE metadata.migrations RENAME TO migracoes;
ALTER TABLE metadata.migracoes RENAME COLUMN version TO versao;
ALTER TABLE metadata.migracoes RENAME COLUMN applied_at TO dt_aplicacao;
ALTER TABLE metadata.migracoes ALTER COLUMN dt_aplicacao SET DATA TYPE TIMESTAMP USING try_cast(dt_aplicacao AS TIMESTAMP);

-- metadata.runs -> metadata.execucoes
ALTER TABLE metadata.runs RENAME TO execucoes;
ALTER TABLE metadata.execucoes RENAME COLUMN id TO id_execucao;
ALTER TABLE metadata.execucoes RENAME COLUMN stage TO etapa;
ALTER TABLE metadata.execucoes RENAME COLUMN source TO fonte;
ALTER TABLE metadata.execucoes RENAME COLUMN year TO particao;
ALTER TABLE metadata.execucoes RENAME COLUMN started_at TO dt_inicio;
ALTER TABLE metadata.execucoes RENAME COLUMN finished_at TO dt_fim;
ALTER TABLE metadata.execucoes RENAME COLUMN code_version TO versao_commit;
ALTER TABLE metadata.execucoes RENAME COLUMN rows_in TO qtd_linhas_entrada;
ALTER TABLE metadata.execucoes RENAME COLUMN rows_out TO qtd_linhas_saida;
ALTER TABLE metadata.execucoes RENAME COLUMN status TO resultado;
ALTER TABLE metadata.execucoes RENAME COLUMN message TO mensagem;
ALTER TABLE metadata.execucoes ALTER COLUMN dt_inicio SET DATA TYPE TIMESTAMP USING try_cast(dt_inicio AS TIMESTAMP);
ALTER TABLE metadata.execucoes ALTER COLUMN dt_fim SET DATA TYPE TIMESTAMP USING try_cast(dt_fim AS TIMESTAMP);
CREATE SEQUENCE metadata.seq_execucoes;
SELECT nextval('metadata.seq_execucoes') FROM range((SELECT coalesce(max(id_execucao), 0) FROM metadata.execucoes));
ALTER TABLE metadata.execucoes ALTER COLUMN id_execucao SET DEFAULT nextval('metadata.seq_execucoes');
DROP SEQUENCE metadata.seq_runs;

-- metadata.captures -> metadata.capturas
ALTER TABLE metadata.captures RENAME TO capturas;
ALTER TABLE metadata.capturas RENAME COLUMN id TO id_captura;
ALTER TABLE metadata.capturas RENAME COLUMN source TO fonte;
ALTER TABLE metadata.capturas RENAME COLUMN year TO particao;
ALTER TABLE metadata.capturas RENAME COLUMN size_bytes TO qtd_bytes;
ALTER TABLE metadata.capturas RENAME COLUMN path TO caminho;
ALTER TABLE metadata.capturas RENAME COLUMN captured_at TO dt_captura;
ALTER TABLE metadata.capturas RENAME COLUMN last_checked_at TO dt_verificacao;
ALTER TABLE metadata.capturas RENAME COLUMN run_id TO id_execucao;
ALTER TABLE metadata.capturas RENAME COLUMN last_modified TO ultima_modificacao;
ALTER TABLE metadata.capturas RENAME COLUMN loaded_at TO dt_carga;
ALTER TABLE metadata.capturas ALTER COLUMN dt_captura SET DATA TYPE TIMESTAMP USING try_cast(dt_captura AS TIMESTAMP);
ALTER TABLE metadata.capturas ALTER COLUMN dt_verificacao SET DATA TYPE TIMESTAMP USING try_cast(dt_verificacao AS TIMESTAMP);
ALTER TABLE metadata.capturas ALTER COLUMN dt_carga SET DATA TYPE TIMESTAMP USING try_cast(dt_carga AS TIMESTAMP);
CREATE SEQUENCE metadata.seq_capturas;
SELECT nextval('metadata.seq_capturas') FROM range((SELECT coalesce(max(id_captura), 0) FROM metadata.capturas));
ALTER TABLE metadata.capturas ALTER COLUMN id_captura SET DEFAULT nextval('metadata.seq_capturas');
DROP SEQUENCE metadata.seq_captures;

-- metadata.capture_items -> metadata.capturas_itens
ALTER TABLE metadata.capture_items RENAME TO capturas_itens;
ALTER TABLE metadata.capturas_itens RENAME COLUMN id TO id_captura_item;
ALTER TABLE metadata.capturas_itens RENAME COLUMN capture_id TO id_captura;
ALTER TABLE metadata.capturas_itens RENAME COLUMN source TO fonte;
ALTER TABLE metadata.capturas_itens RENAME COLUMN status TO status_http;
ALTER TABLE metadata.capturas_itens RENAME COLUMN fetched_at TO dt_busca;
ALTER TABLE metadata.capturas_itens RENAME COLUMN version TO versao;
ALTER TABLE metadata.capturas_itens ALTER COLUMN dt_busca SET DATA TYPE TIMESTAMP USING try_cast(dt_busca AS TIMESTAMP);
CREATE SEQUENCE metadata.seq_capturas_itens;
SELECT nextval('metadata.seq_capturas_itens') FROM range((SELECT coalesce(max(id_captura_item), 0) FROM metadata.capturas_itens));
ALTER TABLE metadata.capturas_itens ALTER COLUMN id_captura_item SET DEFAULT nextval('metadata.seq_capturas_itens');
DROP SEQUENCE metadata.seq_capture_items;

-- metadata.source_checks -> metadata.fontes_verificacoes
ALTER TABLE metadata.source_checks RENAME TO fontes_verificacoes;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN id TO id_verificacao;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN checked_at TO dt_verificacao;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN source TO fonte;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN partition TO particao;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN check_name TO verificacao;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN status TO resultado;
ALTER TABLE metadata.fontes_verificacoes RENAME COLUMN detail TO detalhe;
ALTER TABLE metadata.fontes_verificacoes ALTER COLUMN dt_verificacao SET DATA TYPE TIMESTAMP USING try_cast(dt_verificacao AS TIMESTAMP);
CREATE SEQUENCE metadata.seq_fontes_verificacoes;
SELECT nextval('metadata.seq_fontes_verificacoes') FROM range((SELECT coalesce(max(id_verificacao), 0) FROM metadata.fontes_verificacoes));
ALTER TABLE metadata.fontes_verificacoes ALTER COLUMN id_verificacao SET DEFAULT nextval('metadata.seq_fontes_verificacoes');
DROP SEQUENCE metadata.seq_source_checks;

-- metadata.dbt_results -> metadata.testes_resultados
ALTER TABLE metadata.dbt_results RENAME TO testes_resultados;
ALTER TABLE metadata.testes_resultados RENAME COLUMN run_id TO id_execucao;
ALTER TABLE metadata.testes_resultados RENAME COLUMN unique_id TO id_no;
ALTER TABLE metadata.testes_resultados RENAME COLUMN kind TO tipo;
ALTER TABLE metadata.testes_resultados RENAME COLUMN status TO resultado;
ALTER TABLE metadata.testes_resultados RENAME COLUMN failures TO qtd_falhas;
ALTER TABLE metadata.testes_resultados RENAME COLUMN message TO mensagem;
ALTER TABLE metadata.testes_resultados RENAME COLUMN recorded_at TO dt_registro;
ALTER TABLE metadata.testes_resultados ALTER COLUMN dt_registro SET DATA TYPE TIMESTAMP USING try_cast(dt_registro AS TIMESTAMP);

-- identity.pessoa -> identity.pessoas
ALTER TABLE identity.pessoa RENAME TO pessoas;
ALTER TABLE identity.pessoas RENAME COLUMN created_at TO dt_criacao;
ALTER TABLE identity.pessoas ALTER COLUMN dt_criacao SET DATA TYPE TIMESTAMP USING try_cast(dt_criacao AS TIMESTAMP);
CREATE SEQUENCE identity.seq_pessoas;
SELECT nextval('identity.seq_pessoas') FROM range((SELECT coalesce(max(id_pessoa), 0) FROM identity.pessoas));
ALTER TABLE identity.pessoas ALTER COLUMN id_pessoa SET DEFAULT nextval('identity.seq_pessoas');
DROP SEQUENCE identity.seq_pessoa;

-- identity.pessoa_identificador -> identity.pessoas_identificadores
ALTER TABLE identity.pessoa_identificador RENAME TO pessoas_identificadores;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN source TO fonte;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN id_type TO id_tipo;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN source_id TO id_na_fonte;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN method TO metodo;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN confirmed_by TO confirmado_por;
ALTER TABLE identity.pessoas_identificadores RENAME COLUMN linked_at TO dt_ligacao;
ALTER TABLE identity.pessoas_identificadores ALTER COLUMN dt_ligacao SET DATA TYPE TIMESTAMP USING try_cast(dt_ligacao AS TIMESTAMP);

-- identity.pessoa_fusao -> identity.pessoas_fusoes
ALTER TABLE identity.pessoa_fusao RENAME TO pessoas_fusoes;
ALTER TABLE identity.pessoas_fusoes RENAME COLUMN fundida_em TO dt_fusao;
ALTER TABLE identity.pessoas_fusoes ALTER COLUMN dt_fusao SET DATA TYPE TIMESTAMP USING try_cast(dt_fusao AS TIMESTAMP);

-- Descrições (as colunas mudaram de nome e de tipo)

COMMENT ON TABLE metadata.migracoes IS 'Migrações de `ddl/` já aplicadas neste warehouse. Uma linha por migração.';
COMMENT ON COLUMN metadata.migracoes.versao IS 'Número da migração (por exemplo, 0007).';
COMMENT ON COLUMN metadata.migracoes.dt_aplicacao IS 'Instante (UTC) em que a migração foi aplicada.';

COMMENT ON TABLE metadata.execucoes IS 'Execuções de cada etapa da pipeline (extração, carga, transformação), com contagem de linhas e resultado. Uma linha por execução.';
COMMENT ON COLUMN metadata.execucoes.id_execucao IS 'Identificador da execução.';
COMMENT ON COLUMN metadata.execucoes.etapa IS 'Etapa executada (extract, load, transform_pre, transform_post, freshness...).';
COMMENT ON COLUMN metadata.execucoes.fonte IS 'Fonte processada, quando a etapa é de uma fonte.';
COMMENT ON COLUMN metadata.execucoes.dataset IS 'Dataset processado, quando a etapa é de um dataset.';
COMMENT ON COLUMN metadata.execucoes.particao IS 'Partição processada (ano, mês AAAAMM ou legislatura), quando houver.';
COMMENT ON COLUMN metadata.execucoes.dt_inicio IS 'Instante (UTC) em que a execução começou.';
COMMENT ON COLUMN metadata.execucoes.dt_fim IS 'Instante (UTC) em que a execução terminou.';
COMMENT ON COLUMN metadata.execucoes.versao_commit IS 'Versão do código (commit) que fez a execução.';
COMMENT ON COLUMN metadata.execucoes.qtd_linhas_entrada IS 'Linhas lidas pela etapa.';
COMMENT ON COLUMN metadata.execucoes.qtd_linhas_saida IS 'Linhas gravadas pela etapa.';
COMMENT ON COLUMN metadata.execucoes.resultado IS 'Resultado da execução (running, ok ou error).';
COMMENT ON COLUMN metadata.execucoes.mensagem IS 'Mensagem de erro, quando a execução falhou.';

COMMENT ON TABLE metadata.capturas IS 'Cada arquivo capturado da fonte e guardado no landing, com hash, endereço e data. É a prova do que a fonte entregou. Uma linha por arquivo.';
COMMENT ON COLUMN metadata.capturas.id_captura IS 'Identificador da captura; as tabelas do raw o guardam como _source_file_id.';
COMMENT ON COLUMN metadata.capturas.fonte IS 'Fonte do arquivo.';
COMMENT ON COLUMN metadata.capturas.dataset IS 'Dataset do arquivo.';
COMMENT ON COLUMN metadata.capturas.particao IS 'Partição do arquivo (ano, mês AAAAMM ou legislatura); vazio nos datasets sem partição.';
COMMENT ON COLUMN metadata.capturas.url IS 'Endereço oficial de onde o arquivo foi baixado.';
COMMENT ON COLUMN metadata.capturas.sha256 IS 'Impressão digital (SHA-256) do arquivo: prova que o arquivo guardado é o que a fonte entregou.';
COMMENT ON COLUMN metadata.capturas.qtd_bytes IS 'Tamanho do arquivo em bytes.';
COMMENT ON COLUMN metadata.capturas.caminho IS 'Caminho do arquivo no landing, a partir da pasta de armazenamento.';
COMMENT ON COLUMN metadata.capturas.dt_captura IS 'Instante (UTC) da primeira captura deste conteúdo.';
COMMENT ON COLUMN metadata.capturas.dt_verificacao IS 'Instante (UTC) da última vez que a fonte foi consultada e o conteúdo continuava o mesmo.';
COMMENT ON COLUMN metadata.capturas.id_execucao IS 'Execução (metadata.execucoes.id_execucao) que fez a captura.';
COMMENT ON COLUMN metadata.capturas.etag IS 'ETag que a fonte informou na captura, quando informou.';
COMMENT ON COLUMN metadata.capturas.ultima_modificacao IS 'Cabeçalho Last-Modified que a fonte informou na captura, como publicado, quando informou.';
COMMENT ON COLUMN metadata.capturas.dt_carga IS 'Instante (UTC) em que o arquivo foi carregado no raw; vazio se ainda não foi.';

COMMENT ON TABLE metadata.capturas_itens IS 'Itens buscados um a um nos datasets por item (tramitação, processos...), com o arquivo de lote em que cada resposta foi guardada. Uma linha por item buscado.';
COMMENT ON COLUMN metadata.capturas_itens.id_captura_item IS 'Identificador da linha.';
COMMENT ON COLUMN metadata.capturas_itens.id_captura IS 'Captura (metadata.capturas.id_captura) do lote que guardou a resposta do item.';
COMMENT ON COLUMN metadata.capturas_itens.fonte IS 'Fonte do item.';
COMMENT ON COLUMN metadata.capturas_itens.dataset IS 'Dataset do item.';
COMMENT ON COLUMN metadata.capturas_itens.item IS 'Identificador do item na fonte (por exemplo, o código da proposição).';
COMMENT ON COLUMN metadata.capturas_itens.url IS 'Endereço oficial consultado para este item.';
COMMENT ON COLUMN metadata.capturas_itens.status_http IS 'Código HTTP da resposta (0 quando a fonte não respondeu).';
COMMENT ON COLUMN metadata.capturas_itens.sha256 IS 'Impressão digital (SHA-256) da resposta do item.';
COMMENT ON COLUMN metadata.capturas_itens.dt_busca IS 'Instante (UTC) em que o item foi buscado.';
COMMENT ON COLUMN metadata.capturas_itens.versao IS 'Versão do item na fonte (por exemplo, data da última atualização), usada para saber se ele mudou.';

COMMENT ON TABLE metadata.fontes_verificacoes IS 'Resultado das verificações das fontes e das cargas: disponibilidade, cabeçalho, volume e balanço de cada carga. Uma linha por verificação.';
COMMENT ON COLUMN metadata.fontes_verificacoes.id_verificacao IS 'Identificador da verificação.';
COMMENT ON COLUMN metadata.fontes_verificacoes.dt_verificacao IS 'Instante (UTC) da verificação.';
COMMENT ON COLUMN metadata.fontes_verificacoes.fonte IS 'Fonte verificada.';
COMMENT ON COLUMN metadata.fontes_verificacoes.dataset IS 'Dataset verificado.';
COMMENT ON COLUMN metadata.fontes_verificacoes.particao IS 'Partição verificada (ano, mês AAAAMM ou legislatura), quando houver.';
COMMENT ON COLUMN metadata.fontes_verificacoes.verificacao IS 'Nome da verificação (availability, schema, volume, carga, linhas_removidas...).';
COMMENT ON COLUMN metadata.fontes_verificacoes.resultado IS 'Resultado: ok, warn (aviso) ou error (erro).';
COMMENT ON COLUMN metadata.fontes_verificacoes.detalhe IS 'Detalhe do resultado (contagens, colunas que mudaram, mensagem de erro).';

COMMENT ON TABLE metadata.testes_resultados IS 'Resultado de cada modelo, teste e verificação de frescor do dbt em cada execução. Uma linha por nó e execução.';
COMMENT ON COLUMN metadata.testes_resultados.id_execucao IS 'Execução (metadata.execucoes.id_execucao) que rodou o dbt.';
COMMENT ON COLUMN metadata.testes_resultados.id_no IS 'Identificador do nó no dbt (por exemplo, test.dado_publico_brasil.nome_do_teste).';
COMMENT ON COLUMN metadata.testes_resultados.tipo IS 'Tipo do nó: model, test ou freshness.';
COMMENT ON COLUMN metadata.testes_resultados.resultado IS 'Resultado: success, pass, warn, fail ou error.';
COMMENT ON COLUMN metadata.testes_resultados.qtd_falhas IS 'Linhas que fizeram o teste falhar ou avisar.';
COMMENT ON COLUMN metadata.testes_resultados.mensagem IS 'Mensagem do dbt para o nó.';
COMMENT ON COLUMN metadata.testes_resultados.dt_registro IS 'Instante (UTC) em que o resultado foi gravado.';

COMMENT ON TABLE identity.pessoas IS 'Pessoas do projeto, cada uma com uma chave própria e estável (nunca muda e nunca é reaproveitada). Uma linha por pessoa.';
COMMENT ON COLUMN identity.pessoas.id_pessoa IS 'Chave própria da pessoa no projeto, sem significado fora dele.';
COMMENT ON COLUMN identity.pessoas.dt_criacao IS 'Instante (UTC) em que a pessoa foi criada.';

COMMENT ON TABLE identity.pessoas_identificadores IS 'Identificadores de cada pessoa nas fontes oficiais (tabela-ponte): liga o registro da fonte à chave própria. Uma linha por identificador.';
COMMENT ON COLUMN identity.pessoas_identificadores.fonte IS 'Fonte do identificador (por exemplo, camara, senado, tse).';
COMMENT ON COLUMN identity.pessoas_identificadores.id_tipo IS 'Tipo do identificador na fonte (por exemplo, deputado, senador, candidato).';
COMMENT ON COLUMN identity.pessoas_identificadores.id_na_fonte IS 'Valor do identificador na fonte.';
COMMENT ON COLUMN identity.pessoas_identificadores.id_pessoa IS 'Chave própria da pessoa a que o identificador pertence.';
COMMENT ON COLUMN identity.pessoas_identificadores.metodo IS 'Como o vínculo foi feito: identificador oficial da própria fonte, regra de nome civil e nascimento, ou vínculo aprovado por uma pessoa.';
COMMENT ON COLUMN identity.pessoas_identificadores.confirmado_por IS 'Quem aprovou o vínculo, quando ele foi aprovado à mão.';
COMMENT ON COLUMN identity.pessoas_identificadores.dt_ligacao IS 'Instante (UTC) em que o vínculo foi feito.';

COMMENT ON TABLE identity.pessoas_fusoes IS 'Fusões de chaves: quando se descobre que duas chaves são a mesma pessoa, a mais nova é absorvida pela mais antiga e a fusão fica registrada aqui. Uma linha por fusão.';
COMMENT ON COLUMN identity.pessoas_fusoes.id_pessoa_absorvida IS 'Chave que deixou de existir em identity.pessoas e nunca é reaproveitada.';
COMMENT ON COLUMN identity.pessoas_fusoes.id_pessoa_sobrevivente IS 'Chave que ficou com os identificadores da absorvida.';
COMMENT ON COLUMN identity.pessoas_fusoes.metodo IS 'Regra que mostrou que as duas chaves são a mesma pessoa.';
COMMENT ON COLUMN identity.pessoas_fusoes.dt_fusao IS 'Instante (UTC) em que a fusão foi feita.';
