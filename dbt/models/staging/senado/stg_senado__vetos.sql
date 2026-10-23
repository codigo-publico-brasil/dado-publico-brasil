-- Vetos presidenciais apreciados pelo Congresso: uma linha por veto, com a matéria vetada e a norma gerada.
select
    try_cast(codigo as bigint) as veto_id,
    try_cast(materia_codigo as bigint) as materia_veto_id,
    try_cast(materia_numero as integer) as numero,
    try_cast(materia_ano as integer) as ano,
    try_cast(materia_vetada_codigo as bigint) as materia_vetada_id,
    materia_vetada_sigla,
    materia_vetada_numero,
    try_cast(materia_vetada_ano as integer) as materia_vetada_ano,
    sentence_case(materia_vetada_ementa) as materia_vetada_ementa,
    try_cast(materia_vetada_norma_gerada_codigo_norma as bigint) as norma_id,
    materia_vetada_norma_gerada_nome_norma as norma_nome,
    try_cast(mensagem_numero as integer) as mensagem_numero,
    try_cast(mensagem_ano as integer) as mensagem_ano,
    mensagem_url_planalto as mensagem_url,
    total = 'Sim' as veto_total,
    assunto,
    try_cast(data_recebimento_congresso as date) as recebido_em,
    try_cast(data_publicacao as date) as publicado_em,
    try_cast(data_sobrestacao_pauta as date) as sobrestado_em,
    sobrestando_pauta = 'Sim' as sobrestando_pauta,
    try_cast(quantidade_dispositivos as integer) as quantidade_dispositivos,
    materia_em_tramitacao = 'Sim' as em_tramitacao,
    _source_file_id as source_file_id

from {{ source('senado', 'vetos') }}
