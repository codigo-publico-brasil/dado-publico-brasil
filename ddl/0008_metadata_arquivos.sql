-- Arquivos materializados a partir das capturas do landing (ADR 0037): o que o `export` publica nas coleções `arq_`.
CREATE TABLE metadata.arquivos (
    fonte VARCHAR NOT NULL,
    colecao VARCHAR NOT NULL,
    caminho VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    id_captura BIGINT NOT NULL,
    sha256_arquivo VARCHAR NOT NULL,
    qtd_bytes BIGINT NOT NULL,
    fl_original BOOLEAN NOT NULL,
    PRIMARY KEY (fonte, colecao, caminho)
);
COMMENT ON TABLE metadata.arquivos IS 'Arquivos materializados no disco a partir das capturas do landing (cópia ou extração de pacote), com a captura de origem. Uma linha por arquivo.';
COMMENT ON COLUMN metadata.arquivos.fonte IS 'Fonte oficial do arquivo.';
COMMENT ON COLUMN metadata.arquivos.colecao IS 'Coleção do arquivo (a pasta é arq_ seguida deste nome).';
COMMENT ON COLUMN metadata.arquivos.caminho IS 'Caminho do arquivo relativo à pasta da coleção.';
COMMENT ON COLUMN metadata.arquivos.dataset IS 'Dataset da fonte cuja captura originou o arquivo.';
COMMENT ON COLUMN metadata.arquivos.id_captura IS 'Captura do landing de onde o arquivo veio (o pacote, se foi extraído).';
COMMENT ON COLUMN metadata.arquivos.sha256_arquivo IS 'SHA-256 do arquivo materializado.';
COMMENT ON COLUMN metadata.arquivos.qtd_bytes IS 'Tamanho do arquivo materializado, em bytes.';
COMMENT ON COLUMN metadata.arquivos.fl_original IS 'Verdadeiro se os bytes são idênticos ao arquivo capturado; falso se foi extraído de um pacote.';
