-- O que cada eleito declarou na campanha: total dos bens, das receitas e das despesas contratadas, só fatos e totais.
-- O total é vazio (e não zero) quando o arquivo correspondente ainda não foi carregado ou não traz o candidato.
with bens as (

    select
        b.id_candidatura,
        count(*) as qtd_bens,
        sum(b.valor) as valor_bens,
        max(b.dt_atualizacao) as dt_atualizacao_bens,
        max(cast(k.dt_captura as date)) as dt_captura_bens

    from {{ ref('stg_tse__bens') }} as b

    left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = b.id_captura

    group by b.id_candidatura

),

receitas as (

    select
        r.id_candidatura,
        count(*) as qtd_receitas,
        sum(r.valor) as valor_receitas,
        max(r.dt_prestacao) as dt_prestacao_receitas,
        max(cast(k.dt_captura as date)) as dt_captura_receitas

    from {{ ref('stg_tse__receitas_candidatos') }} as r

    left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = r.id_captura

    group by r.id_candidatura

),

despesas as (

    select
        d.id_candidatura,
        count(*) as qtd_despesas,
        sum(d.valor) as valor_despesas,
        max(d.dt_prestacao) as dt_prestacao_despesas,
        max(cast(k.dt_captura as date)) as dt_captura_despesas

    from {{ ref('stg_tse__despesas_candidatos') }} as d

    left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = d.id_captura

    group by d.id_candidatura

)

select
    '{{ var("source_tse") }}' as fonte,
    e.id_candidatura,
    e.ano_eleicao,
    e.uf,
    e.cargo,
    cast(b.qtd_bens as bigint) as qtd_bens,
    cast(b.valor_bens as decimal(18, 2)) as valor_bens,
    b.dt_atualizacao_bens,
    b.dt_captura_bens,
    cast(r.qtd_receitas as bigint) as qtd_receitas,
    cast(r.valor_receitas as decimal(18, 2)) as valor_receitas,
    cast(d.qtd_despesas as bigint) as qtd_despesas,
    cast(d.valor_despesas as decimal(18, 2)) as valor_despesas,
    greatest(r.dt_prestacao_receitas, d.dt_prestacao_despesas) as dt_prestacao,
    greatest(r.dt_captura_receitas, d.dt_captura_despesas) as dt_captura_contas,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || e.ano_eleicao as fonte_url_bens,
    'https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-' || e.ano_eleicao as fonte_url_contas

from {{ ref('eleitos') }} as e

left join bens as b on b.id_candidatura = e.id_candidatura

left join receitas as r on r.id_candidatura = e.id_candidatura

left join despesas as d on d.id_candidatura = e.id_candidatura
