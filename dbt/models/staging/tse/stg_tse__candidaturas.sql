with source as (

    select * from {{ source('tse', 'candidaturas') }}

)

select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(nr_turno as integer) as turno,
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || sg_ue || ':' || sq_candidato as id_candidatura,
    sg_ue as ue,
    sg_uf as uf,
    sentence_case(ds_cargo) as cargo,
    nr_candidato as numero,
    proper_name(nm_candidato) as nome,
    proper_name(nm_urna_candidato) as nome_urna,
    sentence_case(ds_situacao_candidatura) as situacao_candidatura,
    sg_partido as partido_sigla,
    nm_partido as partido_nome,
    try_strptime(dt_nascimento, '%d/%m/%Y')::date as dt_nascimento,
    sentence_case(ds_genero) as genero,
    sentence_case(nullif(nullif(ds_sit_tot_turno, '#NULO#'), '#NULO')) as resultado,
    _source_file_id as id_captura

from source
