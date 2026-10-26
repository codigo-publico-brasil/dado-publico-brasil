-- Votos de cada candidato (todos os cargos) por município e zona, como o TSE publica. O nome social não entra.
-- Nos arquivos de 2002 e 2010 a unidade eleitoral (`SG_UE`) vem como o código do município até para presidente,
-- governador e deputados: a unidade do cargo é BR para presidente, a UF para os cargos estaduais e federais e o
-- município para prefeito e vereador, igual à das candidaturas.
with source as (

    select
        *,
        case
            when upper(ds_cargo) like '%PRESIDENTE%' and upper(ds_cargo) not like '%VICE-PREFEITO%' then 'BR'
            when upper(ds_cargo) like '%PREFEITO%' or upper(ds_cargo) like '%VEREADOR%' then sg_ue
            else sg_uf
        end as ue_do_cargo

    from {{ source('tse', 'votacao') }}

)

select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(nr_turno as integer) as turno,
    tp_abrangencia as abrangencia,
    sg_uf as uf,
    ue_do_cargo as cd_ue,
    nm_ue as ue_nome,
    try_cast(cd_municipio as integer) as cd_municipio,
    nm_municipio as municipio,
    try_cast(nr_zona as integer) as zona,
    try_cast(cd_cargo as integer) as cd_cargo,
    sentence_case(upper(ds_cargo)) as cargo,  -- caixa mista aqui e maiúsculas nas candidaturas: padroniza igual
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || ue_do_cargo || ':' || sq_candidato as id_candidatura,
    nr_candidato as numero,
    proper_name(nm_candidato) as nome,
    proper_name(nm_urna_candidato) as nome_urna,
    sentence_case(ds_situacao_candidatura) as situacao_candidatura,
    sentence_case(ds_detalhe_situacao_cand) as detalhe_situacao,
    try_cast(nr_partido as integer) as partido_numero,
    sg_partido as partido_sigla,
    nullif(sg_federacao, '#NULO') as federacao_sigla,
    st_voto_em_transito = 'S' as fl_voto_em_transito,
    try_cast(qt_votos_nominais as bigint) as votos_nominais,
    nm_tipo_destinacao_votos as destinacao,
    -- os arquivos de 2002 a 2014 não separam os votos válidos: valem os nominais, que para quem teve a candidatura deferida são os mesmos
    coalesce(try_cast(qt_votos_nominais_validos as bigint), try_cast(qt_votos_nominais as bigint)) as votos_validos,
    -- os arquivos de 1998 a 2010 chamam de `Média` o eleito por média, que depois vira `Eleito por média`
    case when lower(trim(ds_sit_tot_turno)) = 'média' then 'Eleito por média' else sentence_case(nullif(nullif(ds_sit_tot_turno, '#NULO#'), '#NULO')) end as resultado,
    _source_file_id as id_captura

from source

where coalesce(ds_eleicao, '') not ilike '%suplementar%'  -- as suplementares repetem o sequencial das ordinárias e ficam só no raw
