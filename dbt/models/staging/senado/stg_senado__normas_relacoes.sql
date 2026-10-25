-- Relações de cada norma com atos posteriores, como o Senado declara ("vide"): alteração, regulamentação,
-- veto, declaração de constitucionalidade etc. Das leis, leis complementares, emendas e medidas provisórias
-- detalhadas e da Constituição.
with detalhadas as (

    select _dlt_id, try_cast(id as bigint) as id_norma, _source_file_id as id_captura
    from {{ source('senado', 'normas_detalhe') }}

    union all

    select _dlt_id, try_cast(id as bigint), _source_file_id
    from {{ source('senado', 'normas_detalhe_constituicao') }}

),

relacoes as (

    select * from {{ source('senado', 'normas_detalhe__vides_vide') }}

    union all by name

    select * from {{ source('senado', 'normas_detalhe_constituicao__vides_vide') }}

)

select
    d.id_norma,
    r.comentario as tipo_relacao,
    try_cast(r.codnormaposterior as bigint) as id_norma_posterior,
    r.nome_norma_posterior as norma_posterior_nome,
    try_strptime(r.dat_assinatura, '%d/%m/%Y')::date as dt_norma_posterior_assinatura,
    try_strptime(r.datapub, '%d/%m/%Y')::date as dt_publicacao,
    r.nome_pub as publicacao,
    d.id_captura

from relacoes as r

inner join detalhadas as d on d._dlt_id = r._dlt_parent_id
