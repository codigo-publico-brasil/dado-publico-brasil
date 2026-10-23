-- Bens declarados por cada candidato (todos os cargos): uma linha por bem. O valor é o declarado, sem correção.
select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || sq_candidato as candidatura_id,
    sg_uf as uf,
    try_cast(nr_ordem_bem_candidato as integer) as ordem,
    try_cast(cd_tipo_bem_candidato as integer) as tipo_codigo,
    sentence_case(ds_tipo_bem_candidato) as tipo,
    ds_bem_candidato as descricao,
    try_cast(replace(vr_bem_candidato, ',', '.') as decimal(18, 2)) as valor,
    try_strptime(dt_ult_atual_bem_candidato, '%d/%m/%Y')::date as atualizado_em,
    _source_file_id as source_file_id

from {{ source('tse', 'bens') }}
