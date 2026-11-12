-- ADR 0053, item 3: o que o código e os testes liam dentro do texto de `detalhe` passa a ter coluna própria.
-- Migração aditiva: `detalhe` fica, para gente e para auditoria. As linhas antigas são preenchidas por extração
-- determinística do `detalhe`; o que não casa fica vazio (nunca se estima).
ALTER TABLE metadata.fontes_verificacoes ADD COLUMN cd_status_http INTEGER;
ALTER TABLE metadata.fontes_verificacoes ADD COLUMN tipo_ocorrencia VARCHAR;
ALTER TABLE metadata.fontes_verificacoes ADD COLUMN qtd_bytes_esperados BIGINT;
ALTER TABLE metadata.fontes_verificacoes ADD COLUMN qtd_bytes_recebidos BIGINT;
ALTER TABLE metadata.fontes_verificacoes ADD COLUMN qtd_linhas BIGINT;

UPDATE metadata.fontes_verificacoes SET
    cd_status_http = try_cast(regexp_extract(detalhe, 'HTTP (?:Error )?([0-9]{3})', 1) AS INTEGER)
WHERE verificacao IN ('availability', 'bloqueio') AND resultado = 'error';

UPDATE metadata.fontes_verificacoes SET tipo_ocorrencia = CASE
    WHEN verificacao = 'bloqueio' THEN 'bloqueio'
    WHEN detalhe LIKE 'ainda não publicado%' THEN 'nao_publicado'
    WHEN cd_status_http = 404 THEN 'nao_encontrado'
    WHEN cd_status_http IS NOT NULL THEN 'erro_http'
    WHEN detalhe LIKE '%página HTML%' THEN 'html_no_lugar'
    WHEN detalhe LIKE '%a fonte informou%' THEN 'tamanho_divergente'
    WHEN detalhe LIKE '%zip inválido%' OR detalhe LIKE '%membro corrompido%' OR detalhe LIKE '%nenhum membro%' THEN 'zip_invalido'
END
WHERE (verificacao IN ('availability', 'bloqueio') AND resultado = 'error') OR (verificacao = 'integridade' AND resultado = 'error');

UPDATE metadata.fontes_verificacoes SET
    qtd_bytes_esperados = try_cast(regexp_extract(detalhe, 'a fonte informou ([0-9]+)', 1) AS BIGINT),
    qtd_bytes_recebidos = try_cast(regexp_extract(detalhe, 'recebidos ([0-9]+) bytes', 1) AS BIGINT)
WHERE verificacao = 'integridade' AND resultado = 'error';

UPDATE metadata.fontes_verificacoes SET
    qtd_bytes_recebidos = try_cast(regexp_extract(detalhe, '^([0-9]+) bytes$', 1) AS BIGINT)
WHERE verificacao = 'availability' AND resultado = 'ok';

UPDATE metadata.fontes_verificacoes SET qtd_linhas = CASE verificacao
    WHEN 'carga' THEN try_cast(regexp_extract(detalhe, 'carregadas ([0-9]+)', 1) AS BIGINT)
    WHEN 'volume' THEN try_cast(regexp_extract(detalhe, '(?:para |^)([0-9]+) linhas', 1) AS BIGINT)
    WHEN 'linhas_removidas' THEN try_cast(regexp_extract(detalhe, '^([0-9]+) linhas', 1) AS BIGINT)
END
WHERE verificacao IN ('carga', 'volume', 'linhas_removidas');

COMMENT ON COLUMN metadata.fontes_verificacoes.cd_status_http IS 'Código HTTP que a fonte devolveu (404, 403, 429...), quando a ocorrência veio de uma resposta; vazio nas demais.';
COMMENT ON COLUMN metadata.fontes_verificacoes.tipo_ocorrencia IS 'Tipo da ocorrência de uma verificação com erro: nao_encontrado (404), nao_publicado (403 no mês ainda não publicado), erro_http (outro código), falha_de_rede, bloqueio, html_no_lugar, tamanho_divergente ou zip_invalido; vazio quando não há ocorrência.';
COMMENT ON COLUMN metadata.fontes_verificacoes.qtd_bytes_esperados IS 'Tamanho em bytes que a fonte informou (Content-Length), quando a verificação o confrontou com o recebido.';
COMMENT ON COLUMN metadata.fontes_verificacoes.qtd_bytes_recebidos IS 'Tamanho em bytes do arquivo recebido, nas verificações de disponibilidade e de integridade.';
COMMENT ON COLUMN metadata.fontes_verificacoes.qtd_linhas IS 'Linhas da verificação: carregadas (carga), lidas (volume) ou de capturas anteriores que a atual não traz (linhas_removidas).';
