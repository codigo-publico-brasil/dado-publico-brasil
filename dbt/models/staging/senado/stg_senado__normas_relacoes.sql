-- Relações de cada norma com atos posteriores, como o Senado declara ("vide"): alteração, regulamentação,
-- veto, declaração de constitucionalidade etc. Das leis, leis complementares, emendas e medidas provisórias
-- detalhadas e da Constituição.
with detalhadas as (

    select _dlt_id, try_cast(id as bigint) as norma_id, _source_file_id as source_file_id
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
    d.norma_id,
    r.comentario as tipo_relacao,
    try_cast(r.codnormaposterior as bigint) as norma_posterior_id,
    r.nome_norma_posterior as norma_posterior_nome,
    try_strptime(r.dat_assinatura, '%d/%m/%Y')::date as norma_posterior_assinada_em,
    try_strptime(r.datapub, '%d/%m/%Y')::date as publicada_em,
    r.nome_pub as publicacao,
    d.source_file_id

from relacoes as r

inner join detalhadas as d on d._dlt_id = r._dlt_parent_id
