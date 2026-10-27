-- O arquivo traz, junto da eleição ordinária, as renovadas e suplementares do ano (cada uma com o seu `cd_eleicao`, e
-- uma descrição escrita de dezenas de jeitos: `Sup.`, `Suplem.`, `Nova Eleição`, `Majoritária - X`). Em cada ano,
-- unidade, cargo e turno vale o código de eleição que cobre mais unidades no ano: a ordinária cobre milhares, a
-- suplementar uma ou duas (issue 74).
with source as (

    select * from {{ source('tse', 'candidaturas') }}

),

coverage as (

    select ano_eleicao, ds_cargo, cd_eleicao, count(distinct sg_ue) as unidades

    from source

    group by all

),

ordinary as (

    select s.*

    from source as s

    left join coverage as c
        on c.ano_eleicao = s.ano_eleicao and c.ds_cargo = s.ds_cargo and c.cd_eleicao is not distinct from s.cd_eleicao

    qualify dense_rank() over (
        partition by s.ano_eleicao, s.sg_ue, s.ds_cargo, s.nr_turno
        order by c.unidades desc nulls last, try_cast(s.cd_eleicao as integer)
    ) = 1

)

select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(nr_turno as integer) as turno,
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || sg_ue || ':' || sq_candidato as id_candidatura,
    try_cast(cd_eleicao as integer) as cd_eleicao,
    ds_eleicao as eleicao,
    sg_ue as ue,
    proper_name(nm_ue) as ue_nome,
    sg_uf as uf,
    sentence_case(ds_cargo) as cargo,
    nr_candidato as numero,
    try_cast(cd_cargo as integer) as cd_cargo,
    nr_partido as numero_partido,
    proper_name(nm_candidato) as nome,
    proper_name(nm_urna_candidato) as nome_urna,
    sentence_case(ds_situacao_candidatura) as situacao_candidatura,
    sg_partido as partido_sigla,
    nm_partido as partido_nome,
    try_strptime(dt_nascimento, '%d/%m/%Y')::date as dt_nascimento,
    sentence_case(ds_genero) as genero,
    -- os arquivos de 1998 a 2010 chamam de `Média` o eleito por média, que depois vira `Eleito por média`
    case when lower(trim(ds_sit_tot_turno)) = 'média' then 'Eleito por média' else sentence_case(nullif(nullif(ds_sit_tot_turno, '#NULO#'), '#NULO')) end as resultado,
    proper_name(tse_value(nm_social_candidato)) as nome_social,
    sentence_case(tse_value(ds_grau_instrucao)) as grau_instrucao,
    sentence_case(tse_value(ds_estado_civil)) as estado_civil,
    sentence_case(tse_value(ds_ocupacao)) as ocupacao,
    tse_value(sg_uf_nascimento) as uf_nascimento,
    tse_value(nm_coligacao) as coligacao_nome,
    tse_value(ds_composicao_coligacao) as coligacao_composicao,
    tse_value(sg_federacao) as federacao_sigla,
    tse_value(ds_composicao_federacao) as federacao_composicao,
    _source_file_id as id_captura

from ordinary

where coalesce(ds_eleicao, '') not ilike '%suplementar%'  -- as eleições suplementares repetem o sequencial das ordinárias e ficam no raw
