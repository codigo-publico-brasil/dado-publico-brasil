-- Vetos presidenciais apreciados pelo Congresso: uma linha por veto, com a matéria vetada e a norma gerada.
select
    try_cast(codigo as bigint) as id_veto,
    try_cast(materia_codigo as bigint) as id_materia_veto,
    try_cast(materia_numero as integer) as numero,
    try_cast(materia_ano as integer) as ano,
    try_cast(materia_vetada_codigo as bigint) as id_materia_vetada,
    materia_vetada_sigla,
    materia_vetada_numero,
    try_cast(materia_vetada_ano as integer) as materia_vetada_ano,
    sentence_case(materia_vetada_ementa) as materia_vetada_ementa,
    try_cast(materia_vetada_norma_gerada_codigo_norma as bigint) as id_norma,
    materia_vetada_norma_gerada_nome_norma as norma_nome,
    try_cast(mensagem_numero as integer) as mensagem_numero,
    try_cast(mensagem_ano as integer) as mensagem_ano,
    mensagem_url_planalto as mensagem_url,
    total = 'Sim' as fl_veto_total,
    assunto,
    try_cast(data_recebimento_congresso as date) as dt_recebimento,
    try_cast(data_publicacao as date) as dt_publicacao,
    try_cast(data_sobrestacao_pauta as date) as dt_sobrestamento,
    sobrestando_pauta = 'Sim' as fl_sobrestando_pauta,
    try_cast(quantidade_dispositivos as integer) as quantidade_dispositivos,
    materia_em_tramitacao = 'Sim' as fl_em_tramitacao,
    _source_file_id as id_captura

from {{ source('senado', 'vetos') }}
