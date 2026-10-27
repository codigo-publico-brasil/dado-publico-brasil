-- A campanha de cada candidatura, só com arquivos do TSE: bens declarados, receitas e despesas da prestação de contas.
-- Uma linha por candidatura que tenha ao menos um desses dados. Total vazio (e não zero) quando o arquivo daquele dado não
-- foi carregado ou não traz o candidato; a lacuna aparece em teste, não escondida em zero.
with bens as (

    select id_candidatura, count(*) as qtd_bens, sum(valor) as valor_bens, max(id_captura) as id_captura_bens
    from {{ ref('stg_tse__bens') }}
    group by 1

),

receitas as (

    select
        id_candidatura,
        count(*) as qtd_receitas,
        sum(valor) as valor_receitas,
        max(dt_prestacao) as dt_prestacao,
        max(id_captura) as id_captura_receitas
    from {{ ref('stg_tse__receitas_candidatos') }}
    group by 1

),

despesas as (

    select
        id_candidatura,
        count(*) as qtd_despesas,
        sum(valor) as valor_despesas,
        max(dt_prestacao) as dt_prestacao,
        max(id_captura) as id_captura_despesas
    from {{ ref('stg_tse__despesas_candidatos') }}
    group by 1

),

candidaturas as (

    select id_candidatura from bens
    union
    select id_candidatura from receitas
    union
    select id_candidatura from despesas

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    cast(b.qtd_bens as bigint) as qtd_bens,
    cast(b.valor_bens as decimal(18, 2)) as valor_bens,
    cast(r.qtd_receitas as bigint) as qtd_receitas,
    cast(r.valor_receitas as decimal(18, 2)) as valor_receitas,
    cast(d.qtd_despesas as bigint) as qtd_despesas,
    cast(d.valor_despesas as decimal(18, 2)) as valor_despesas,
    greatest(r.dt_prestacao, d.dt_prestacao) as dt_prestacao,
    b.id_captura_bens,
    r.id_captura_receitas,
    d.id_captura_despesas

from candidaturas as c

left join bens as b on b.id_candidatura = c.id_candidatura

left join receitas as r on r.id_candidatura = c.id_candidatura

left join despesas as d on d.id_candidatura = c.id_candidatura
