-- Emendas parlamentares ao orçamento, como o Portal da Transparência publica: uma linha por emenda, localidade, função,
-- programa e ação, com os valores empenhado, liquidado e pago. O autor vem pelo nome e pelo código do SIAFI, que não é o
-- código do parlamentar na Câmara ou no Senado. A pessoa (`id_pessoa`) é DERIVADA, só para emenda individual, quando o
-- nome do autor, sem acento e caixa, é o nome parlamentar ou o nome civil de UMA só pessoa que exerceu mandato federal
-- no ano da emenda ou no anterior (a emenda é proposta no ano anterior ao do orçamento) e o código do autor tem um só
-- nome na fonte (ADR 0056). Zero ou mais de uma pessoa, emenda de bancada, de comissão ou de relator e emenda sem
-- autor ficam sem pessoa: nunca se completa nem se escolhe entre homônimos.
with autores as (

    select cd_autor, ano, any_value(name_key(autor_nome)) as nome_chave

    from {{ ref('stg_transparencia__emendas') }}

    where cd_autor is not null and autor_nome is not null and tipo like 'Emenda Individual%'

        -- o mesmo código com dois nomes (em qualquer ano) não liga sozinho
        and cd_autor not in (
            select cd_autor from {{ ref('stg_transparencia__emendas') }}
            where autor_nome is not null group by cd_autor having count(distinct name_key(autor_nome)) > 1
        )

    group by cd_autor, ano

),

nomes_de_pessoas as (

    -- uma chave por nome, para ligar por igualdade (join por hash); `in (f(a), f(b))` ou `or` na condição vira produto cartesiano
    select id_pessoa, name_key(nome_publico) as chave, true as por_nome_parlamentar from {{ ref('dim_pessoas') }}

    union all

    select id_pessoa, name_key(nome_civil), false from {{ ref('dim_pessoas') }} where nome_civil is not null

),

candidatas as (

    select
        a.cd_autor,
        a.ano,
        n.id_pessoa,
        n.por_nome_parlamentar

    from autores as a

    inner join nomes_de_pessoas as n on a.nome_chave = n.chave

    where exists (
        select 1 from {{ ref('fct_exercicios') }} as x
        where x.id_pessoa = n.id_pessoa
            and year(x.dt_inicio) <= a.ano
            and year(coalesce(x.dt_fim, x.dt_mandato_fim, current_date)) >= a.ano - 1
    )

),

ligadas as (

    select
        cd_autor,
        ano,
        any_value(id_pessoa) as id_pessoa,
        if(bool_or(por_nome_parlamentar), 'nome_parlamentar_e_exercicio', 'nome_civil_e_exercicio') as regra

    from candidatas

    group by cd_autor, ano

    having count(distinct id_pessoa) = 1

)

select
    'transparencia' as fonte,
    e.cd_emenda,
    e.ano,
    e.tipo,
    e.cd_autor,
    e.autor_nome,
    l.id_pessoa,
    l.regra as regra_ligacao_pessoa,
    case when l.id_pessoa is not null then 'derivada' end as precisao_ligacao_pessoa,
    e.numero,
    e.localidade,
    e.municipio_ibge,
    e.municipio,
    e.uf,
    e.regiao,
    e.funcao,
    e.subfuncao,
    e.cd_programa,
    e.programa,
    e.cd_acao,
    e.acao,
    e.plano_orcamentario,
    e.valor_empenhado,
    e.valor_liquidado,
    e.valor_pago,
    e.valor_restos_a_pagar_inscritos,
    e.valor_restos_a_pagar_cancelados,
    e.valor_restos_a_pagar_pagos,
    e.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__emendas') }} as e

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = e.id_captura

left join ligadas as l on l.cd_autor = e.cd_autor and l.ano = e.ano
