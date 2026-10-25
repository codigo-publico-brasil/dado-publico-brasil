-- Publicações de cada norma no Diário Oficial (a original e, por exemplo, a do veto), das leis, leis complementares,
-- emendas e medidas provisórias detalhadas e da Constituição.
with detalhadas as (

    select _dlt_id, try_cast(id as bigint) as id_norma, _source_file_id as id_captura
    from {{ source('senado', 'normas_detalhe') }}

    union all

    select _dlt_id, try_cast(id as bigint), _source_file_id
    from {{ source('senado', 'normas_detalhe_constituicao') }}

),

publicacoes as (

    select * from {{ source('senado', 'normas_detalhe__publicacoes_publicacao') }}

    union all by name

    select * from {{ source('senado', 'normas_detalhe_constituicao__publicacoes_publicacao') }}

)

select
    d.id_norma,
    try_cast(p.id as bigint) as id_publicacao,
    p.tipo as tipo_sigla,
    p.fonte as veiculo,
    try_strptime(p.data, '%d/%m/%Y')::date as dt_publicacao,
    p.pagina,
    p.coluna,
    p.tem_texto = 'S' as fl_tem_texto,
    d.id_captura

from publicacoes as p

inner join detalhadas as d on d._dlt_id = p._dlt_parent_id
