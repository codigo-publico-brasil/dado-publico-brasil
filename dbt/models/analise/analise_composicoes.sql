{{ config(alias='composicoes') }}

-- Quem ocupa cada cargo em cada corte, por território e partido. Dois cortes por ano (1º de janeiro e 1º de julho) de 1997
-- até hoje. As duas composições são SEMPRE separadas, porque respondem coisas diferentes:
--  - eleita: quem foi eleito para o mandato que cobre o corte (fatos.mandatos, de dt_inicio a dt_fim_prevista; o fim é
--    derivado da duração do cargo, então cassação, renúncia e morte não entram). Todos os cargos, inclusive vereador.
--  - exercicio: quem de fato exercia o cargo no corte (fatos.exercicios, períodos oficiais da Câmara e do Senado). Só
--    deputado federal e senador; o partido é o mais recente conhecido até o corte (fatos.pessoas_partidos).
-- Mandato sem início (vereador com data impossível, deputado estadual de 2026) não aparece na eleita.
with cortes as (

    select cast(make_date(ano, mes, 1) as date) as dt_corte

    from range(1997, year(current_date) + 1) as a(ano)

    cross join (values (1), (7)) as m(mes)

    where make_date(ano, mes, 1) <= current_date

),

eleita as (

    select
        c.dt_corte,
        'eleita' as tipo_composicao,
        m.id_cargo,
        m.id_territorio,
        m.id_partido,
        count(*) as qtd_membros

    from cortes as c

    inner join {{ ref('fatos_mandatos') }} as m
        on m.dt_inicio is not null and c.dt_corte between m.dt_inicio and m.dt_fim_prevista

    group by all

),

partido_datado as (

    select
        id_pessoa,
        id_partido,
        coalesce(dt_inicio, make_date(ano_referencia, 1, 1)) as dt_partido

    from {{ ref('fatos_pessoas_partidos') }}

    where id_pessoa is not null and id_partido is not null

),

em_exercicio as (

    select
        c.dt_corte,
        x.id_pessoa,
        x.id_cargo,
        u.id_territorio

    from cortes as c

    inner join {{ ref('fatos_exercicios') }} as x
        on x.id_pessoa is not null and c.dt_corte between x.dt_inicio and coalesce(x.dt_fim, current_date)

    left join {{ ref('territorios') }} as u on u.tipo = 'uf' and u.sigla = x.uf

),

exercicio as (

    select
        e.dt_corte,
        'exercicio' as tipo_composicao,
        e.id_cargo,
        e.id_territorio,
        p.id_partido,
        count(*) as qtd_membros

    from em_exercicio as e

    asof left join partido_datado as p on p.id_pessoa = e.id_pessoa and e.dt_corte >= p.dt_partido

    group by all

)

select * from eleita

union all

select * from exercicio
