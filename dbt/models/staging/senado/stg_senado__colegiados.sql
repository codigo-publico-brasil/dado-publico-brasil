-- Colegiados em atividade, como o Senado publica (o extinto não consta do arquivo).
with base as (

select
    try_cast(codigo as bigint) as id_colegiado,
    sigla,
    nome,
    try_cast(data_inicio as date) as dt_inicio,
    publica = 'S' as fl_publico,
    sigla_tipo_colegiado as tipo_sigla,
    descricao_tipo_colegiado as tipo,
    sigla_casa as casa_sigla,
    _source_file_id as id_captura

from {{ source('senado', 'colegiados') }}

)

{{ colunas_auditoria('base') }}
