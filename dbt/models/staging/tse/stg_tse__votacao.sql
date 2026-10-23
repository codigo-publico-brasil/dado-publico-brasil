-- Votos de cada candidato (todos os cargos) por município e zona, como o TSE publica. O nome social não entra.
select
    try_cast(ano_eleicao as integer) as ano_eleicao,
    try_cast(nr_turno as integer) as turno,
    tp_abrangencia as abrangencia,
    sg_uf as uf,
    sg_ue as ue_codigo,
    nm_ue as ue_nome,
    try_cast(cd_municipio as integer) as municipio_codigo,
    nm_municipio as municipio,
    try_cast(nr_zona as integer) as zona,
    try_cast(cd_cargo as integer) as cargo_codigo,
    sentence_case(upper(ds_cargo)) as cargo,  -- caixa mista aqui e maiúsculas nas candidaturas: padroniza igual
    try_cast(sq_candidato as bigint) as sq_candidato,
    ano_eleicao || ':' || sq_candidato as candidatura_id,
    nr_candidato as numero,
    proper_name(nm_candidato) as nome,
    proper_name(nm_urna_candidato) as nome_urna,
    sentence_case(ds_situacao_candidatura) as situacao_candidatura,
    sentence_case(ds_detalhe_situacao_cand) as detalhe_situacao,
    try_cast(nr_partido as integer) as partido_numero,
    sg_partido as partido_sigla,
    nullif(sg_federacao, '#NULO') as federacao_sigla,
    st_voto_em_transito = 'S' as voto_em_transito,
    try_cast(qt_votos_nominais as bigint) as votos_nominais,
    nm_tipo_destinacao_votos as destinacao,
    try_cast(qt_votos_nominais_validos as bigint) as votos_validos,
    sentence_case(nullif(nullif(ds_sit_tot_turno, '#NULO#'), '#NULO')) as resultado,
    _source_file_id as source_file_id

from {{ source('tse', 'votacao') }}
