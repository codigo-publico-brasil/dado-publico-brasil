-- Territórios do país: o Brasil, as UFs e os municípios, com chave do IBGE e o código do TSE quando existe. Os códigos
-- das UFs vêm dos dois primeiros dígitos do código do município (a estrutura oficial do IBGE: 2 da UF e 5 do município).
with municipios as (

    select * from {{ ref('stg_ibge__municipios') }}

),

ufs as (

    select
        cast(id_municipio // 100000 as varchar) as id_territorio,
        'uf' as tipo,
        any_value(uf_nome) as nome,
        uf as sigla,
        'BR' as id_territorio_pai,
        any_value(regiao_sigla) as regiao_sigla,
        cast(null as varchar) as cd_municipio_tse,
        max(id_captura) as id_captura

    from municipios

    group by uf, id_municipio // 100000

),

cidades as (

    select
        cast(m.id_municipio as varchar) as id_territorio,
        'municipio' as tipo,
        m.nome,
        cast(null as varchar) as sigla,
        cast(m.id_municipio // 100000 as varchar) as id_territorio_pai,
        m.regiao_sigla,
        t.cd_municipio_tse,
        m.id_captura

    from municipios as m

    left join {{ ref('municipios_codigos_tse') }} as t on t.id_municipio = m.id_municipio

),

pais as (

    select
        'BR' as id_territorio,
        'pais' as tipo,
        'Brasil' as nome,
        'BR' as sigla,
        cast(null as varchar) as id_territorio_pai,
        cast(null as varchar) as regiao_sigla,
        cast(null as varchar) as cd_municipio_tse,
        max(id_captura) as id_captura

    from municipios

),

todos as (

    select * from pais
    union all
    select * from ufs
    union all
    select * from cidades

)

select 'ibge' as fonte, * from todos
