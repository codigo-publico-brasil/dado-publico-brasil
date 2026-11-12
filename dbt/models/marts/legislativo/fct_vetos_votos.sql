-- Voto nominal de deputados e senadores em cada dispositivo vetado votado, como a fonte entrega: nome, partido e UF,
-- sem o código do parlamentar. A pessoa (`id_pessoa`) é DERIVADA (ADR 0057): o nome, sem acento e caixa, é o nome
-- parlamentar ou o nome civil de UMA só pessoa que exercia o cargo da casa (deputado federal ou senador), nessa UF, no
-- dia da sessão. Zero ou mais de uma pessoa: fica sem pessoa; nunca se escolhe entre homônimos. Uma linha por
-- dispositivo e voto.
with votos as (

    select
        v.*,
        d.dt_sessao,
        name_key(v.nome_parlamentar) as nome_chave,
        case v.casa when 'Câmara' then 'deputado_federal' when 'Senado' then 'senador' end as id_cargo

    from {{ ref('stg_senado__vetos_votos') }} as v

    left join {{ ref('stg_senado__vetos_dispositivos') }} as d on d.id_dispositivo = v.id_dispositivo

),

nomes_de_pessoas as (

    -- uma chave por nome, para ligar por igualdade (join por hash); `in (f(a), f(b))` ou `or` na condição vira produto cartesiano
    select id_pessoa, name_key(nome_publico) as chave, true as por_nome_parlamentar from {{ ref('dim_pessoas') }}

    union all

    select id_pessoa, name_key(nome_civil), false from {{ ref('dim_pessoas') }} where nome_civil is not null

),

candidatas as (

    select
        v.id_dispositivo,
        v.casa,
        v.nome_chave,
        v.uf,
        n.id_pessoa,
        n.por_nome_parlamentar

    from (select distinct id_dispositivo, casa, nome_chave, uf, id_cargo, dt_sessao from votos) as v

    inner join nomes_de_pessoas as n on v.nome_chave = n.chave

    where exists (
        select 1 from {{ ref('fct_exercicios') }} as x
        where x.id_pessoa = n.id_pessoa
            and x.id_cargo = v.id_cargo
            and x.uf = v.uf
            and v.dt_sessao between x.dt_inicio and coalesce(x.dt_fim, x.dt_mandato_fim, current_date)
    )

),

ligadas as (

    select
        id_dispositivo,
        casa,
        nome_chave,
        uf,
        any_value(id_pessoa) as id_pessoa,
        if(bool_or(por_nome_parlamentar), 'nome_parlamentar_e_exercicio', 'nome_civil_e_exercicio') as regra

    from candidatas

    group by id_dispositivo, casa, nome_chave, uf

    having count(distinct id_pessoa) = 1

)

select
    '{{ var("source_senado") }}' as fonte,
    v.id_dispositivo,
    v.casa,
    v.nome_parlamentar,
    l.id_pessoa,
    l.regra as regra_ligacao_pessoa,
    case when l.id_pessoa is not null then 'derivada' end as precisao_ligacao_pessoa,
    v.partido,
    v.uf,
    v.voto,
    v.sessao,
    v.id_captura,
    cast(c.dt_captura as date) as dt_captura

from votos as v

left join ligadas as l
    on l.id_dispositivo = v.id_dispositivo and l.casa = v.casa and l.nome_chave = v.nome_chave and l.uf = v.uf

left join {{ ref('stg_metadata__capturas') }} as c on c.id_captura = v.id_captura
