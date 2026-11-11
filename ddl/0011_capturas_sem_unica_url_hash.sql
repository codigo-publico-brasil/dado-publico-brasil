-- O mesmo conteúdo pode voltar: a fonte serve A, depois B, depois A de novo. A UNIQUE (url, sha256) fazia a
-- volta a A atualizar a captura antiga em vez de criar uma nova, e o "vigente" (maior id da URL) seguia B.
-- Sem a restrição, a volta é uma captura nova (histórico auditável). O DuckDB não remove restrição: recria a tabela.
CREATE TABLE metadata.capturas_nova (
    id_captura BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_capturas'),
    fonte VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    particao INTEGER,
    url VARCHAR NOT NULL,
    sha256 VARCHAR NOT NULL,
    qtd_bytes BIGINT NOT NULL,
    caminho VARCHAR NOT NULL,
    dt_captura TIMESTAMP NOT NULL,
    dt_verificacao TIMESTAMP NOT NULL,
    id_execucao BIGINT,
    etag VARCHAR,
    ultima_modificacao VARCHAR,
    dt_carga TIMESTAMP
);
INSERT INTO metadata.capturas_nova SELECT * FROM metadata.capturas;
DROP TABLE metadata.capturas;
ALTER TABLE metadata.capturas_nova RENAME TO capturas;

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
