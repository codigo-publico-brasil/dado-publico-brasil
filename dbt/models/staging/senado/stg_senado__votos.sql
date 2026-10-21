with votos as (

    select * from {{ source('senado', 'votacoes__votos') }}

),

votacoes as (

    select _dlt_id, codigo_sessao_votacao, _source_file_id from {{ source('senado', 'votacoes') }}

)

select
    try_cast(votacoes.codigo_sessao_votacao as bigint) as votacao_id,
    try_cast(votos.codigo_parlamentar as bigint) as senador_id,
    proper_name(votos.nome_parlamentar) as nome,
    votos.sigla_voto_parlamentar as voto,
    votos.sigla_partido_parlamentar as partido_sigla,
    votos.sigla_uf_parlamentar as uf_sigla,
    votacoes._source_file_id as source_file_id

from votos

inner join votacoes on votacoes._dlt_id = votos._dlt_parent_id
