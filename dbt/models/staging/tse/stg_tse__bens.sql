-- Bens declarados por cada candidato (todos os cargos): uma linha por bem. O valor é o declarado, sem correção.
select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || sg_ue || ':' || sq_candidato as id_candidatura,
    sg_ue as ue,
    sg_uf as uf,
    try_cast(nr_ordem_bem_candidato as integer) as ordem,
    try_cast(cd_tipo_bem_candidato as integer) as cd_tipo,
    sentence_case(ds_tipo_bem_candidato) as tipo,
    ds_bem_candidato as descricao,
    try_cast(replace(vr_bem_candidato, ',', '.') as decimal(18, 2)) as valor,
    try_strptime(dt_ult_atual_bem_candidato, '%d/%m/%Y')::date as dt_atualizacao,
    _source_file_id as id_captura

from {{ tse_source('bens') }}

where coalesce(ds_eleicao, '') not ilike '%suplementar%'  -- as suplementares repetem o sequencial das ordinárias e ficam só no raw

-- de cada candidato vale a declaração da captura mais recente: bem alterado ou retirado não soma duas vezes
qualify _source_file_id = max(_source_file_id) over (partition by ano_eleicao, sq_candidato)
