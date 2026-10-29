-- Quem ocupa cada cargo, uma linha por período de ocupação; o aplicativo filtra a data (dt_inicio <= data <= dt_fim_prevista)
-- e o cargo. Só leitura dos fatos e do núcleo.
--  - Deputado federal e senador: o exercício que a Câmara e o Senado publicam (`tipo_registro` = exercicio), com o fim real
--    quando há (cassação, renúncia, morte, licença) e o suplente que assumiu, inclusive o eleito em eleição suplementar.
--    Quem foi eleito e ainda não assumiu (ou não tem exercício na fonte) entra pelo mandato.
--  - Os demais cargos: o mandato da eleição (`tipo_registro` = mandato), com o fim previsto pela duração do cargo. Não há
--    fonte de exercício para eles, então cassação e renúncia não aparecem (issue 162).
-- Sem data de posse (por exemplo, deputado estadual de 2026, cuja data está nas constituições estaduais), o mandato entra com
-- `dt_inicio` vazio e `ano_inicio` preenchido.
--
-- `tipo_mandato` compara o mandato com o anterior da mesma pessoa no mesmo cargo (e na mesma unidade, abaixo do nível
-- federal): reeleito se o anterior é da eleição de um mandato atrás, retorno se há um intervalo, novato se não há anterior
-- e a base de eleições já cobria o ciclo anterior (senão fica vazio: sem prova nada é afirmado). Vale só para quem tem
-- mandato eleito; o suplente que assumiu fica sem tipo.
with mandatos as (

    select
        m.*,
        cast(substr(m.id_eleicao, 1, 4) as integer) as ano_eleicao,
        c.nome as cargo,
        c.duracao_anos,
        c.esfera

    from {{ ref('fct_mandatos') }} as m

    inner join {{ ref('dim_cargos') }} as c on c.id_cargo = m.id_cargo

),

anteriores as (

    select
        *,
        -- cada cargo conta à parte: quem foi titular e depois vice não é "reeleito"
        lag(ano_eleicao) over (
            partition by id_pessoa, id_cargo, if(esfera = 'federal', '', id_territorio)
            order by ano_eleicao
        ) as ano_anterior,
        min(ano_eleicao) over (partition by id_cargo) as primeiro_ano_do_cargo

    from mandatos

    where id_pessoa is not null

),

mandatos_tipados as (

    select
        *,
        case
            when ano_anterior is not null and ano_eleicao - ano_anterior = duracao_anos then 'reeleito'
            when ano_anterior is not null then 'retorno'
            when ano_eleicao - duracao_anos >= primeiro_ano_do_cargo then 'novato'
        end as tipo_mandato

    from anteriores

),

exercicios as (

    select * from {{ ref('fct_exercicios') }} where id_pessoa is not null

),

-- o mandato que cada exercício cumpre (a janela do mandato contém o início do exercício); sem mandato, é suplente
-- ou eleito em eleição suplementar
exercicio_do_mandato as (

    select
        e.id_exercicio,
        m.id_candidatura,
        m.id_partido,
        m.base_eleicao,
        m.tipo_mandato

    from exercicios as e

    inner join mandatos_tipados as m
        on m.id_pessoa = e.id_pessoa
        and m.id_cargo = e.id_cargo
        and e.dt_inicio between m.dt_inicio and m.dt_fim_prevista

    qualify row_number() over (partition by e.id_exercicio order by m.dt_inicio desc) = 1

),

partido_da_pessoa as (

    -- sem mandato correspondente, o partido que a pessoa tinha no ano do início do exercício (o último registrado até lá)
    select e.id_exercicio, arg_max(pp.id_partido, pp.ano_referencia) as id_partido

    from exercicios as e

    inner join {{ ref('fct_pessoas_partidos') }} as pp
        on pp.id_pessoa = e.id_pessoa and pp.ano_referencia <= year(e.dt_inicio)

    group by e.id_exercicio

),

ocupacao_por_exercicio as (

    select
        em.id_candidatura,
        e.id_pessoa,
        c.nome as cargo,
        t.nome as territorio,
        coalesce(em.id_partido, pd.id_partido) as id_partido,
        year(e.dt_inicio) as ano_inicio,
        e.dt_inicio,
        'informado' as base_do_inicio,
        coalesce(e.dt_fim, e.dt_mandato_fim) as dt_fim_prevista,
        if(e.dt_fim is not null, 'informado', 'derivado') as base_do_fim,
        em.base_eleicao,
        em.tipo_mandato,
        'exercicio' as tipo_registro,
        e.id_captura

    from exercicios as e

    inner join {{ ref('dim_cargos') }} as c on c.id_cargo = e.id_cargo

    left join exercicio_do_mandato as em on em.id_exercicio = e.id_exercicio

    left join partido_da_pessoa as pd on pd.id_exercicio = e.id_exercicio

    left join {{ ref('dim_territorios') }} as t on t.tipo = 'uf' and t.sigla = e.uf

    where e.dt_inicio is not null

),

ocupacao_por_mandato as (

    select
        m.id_candidatura,
        m.id_pessoa,
        m.cargo,
        t.nome as territorio,
        m.id_partido,
        m.ano_eleicao + 1 as ano_inicio,
        m.dt_inicio,
        m.base_dt_inicio as base_do_inicio,
        m.dt_fim_prevista,
        'derivado' as base_do_fim,
        m.base_eleicao,
        m.tipo_mandato,
        'mandato' as tipo_registro,
        m.id_captura

    from mandatos_tipados as m

    left join {{ ref('dim_territorios') }} as t on t.id_territorio = m.id_territorio

    -- deputado federal e senador com exercício registrado já estão no outro ramo
    where not (
        m.id_cargo in ('deputado_federal', 'senador')
        and exists (
            select 1 from exercicios as e
            where e.id_pessoa = m.id_pessoa
                and e.id_cargo = m.id_cargo
                and e.dt_inicio <= m.dt_fim_prevista
                and coalesce(e.dt_fim, date '9999-12-31') >= m.dt_inicio
        )
    )

),

ocupacao as (

    select * from ocupacao_por_exercicio

    union all

    select * from ocupacao_por_mandato

)

select
    o.id_candidatura,
    o.id_pessoa,
    p.nome_publico as nome,
    o.cargo,
    o.territorio,
    pa.sigla as partido,
    o.ano_inicio,
    o.dt_inicio,
    o.base_do_inicio,
    o.dt_fim_prevista,
    o.base_do_fim,
    o.base_eleicao,
    o.tipo_mandato,
    o.tipo_registro,
    cap.url as fonte_url,
    cast(cap.dt_captura as date) as dt_captura

from ocupacao as o

inner join {{ ref('dim_pessoas') }} as p on p.id_pessoa = o.id_pessoa

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = o.id_partido

left join {{ ref('stg_metadata__captures') }} as cap on cap.id_captura = o.id_captura
