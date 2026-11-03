-- Cada período em que alguém exerceu de fato um mandato federal, como a fonte oficial publica:
--  - Câmara: o histórico do deputado é uma sequência de entradas e saídas; o período vai de uma entrada em exercício
--    (posse, reassunção, suplente que assume) até a primeira saída seguinte (licença, vacância, fim de mandato).
--  - Senado: os períodos de exercício já vêm prontos, de titular e de suplentes.
-- Sem fim quando o período está em curso. Vereador, prefeito, governador e presidente não entram: não há fonte oficial
-- de exercício carregada para eles (o mandato deles está em fct_mandatos).
-- Três colunas ligam o período ao resto e são DERIVADAS, marcadas: `id_candidatura` (o mandato que o período cumpre: o
-- início cai dentro da janela do mandato, com 31 dias de folga para registro antes da posse; vazio para o suplente que não
-- foi eleito), `id_territorio` (a UF da fonte em dim_territorios) e `id_partido` com `base_partido` (informado: o partido do
-- histórico da Câmara no início do período; derivado: o último registrado até o ano do início, em fct_pessoas_partidos).
with marcos as (

    -- um marco por deputado, legislatura e instante: entrada em exercício ou saída dele. A convocação de suplente não é
    -- saída, e dois registros no mesmo instante valem um só (a condição mais informativa vence: efetivado, depois titular).
    select
        id_deputado,
        id_legislatura,
        dt_registro,
        bool_or(situacao = 'Exercício') as entra,
        arg_max(condicao_eleitoral, case condicao_eleitoral when 'EFETIVADO' then 2 when 'Titular' then 1 else 0 end)
            filter (where situacao = 'Exercício') as condicao_eleitoral,
        any_value(uf_sigla) as uf_sigla,
        max(descricao) filter (where situacao <> 'Exercício') as descricao_saida,
        max(id_captura) as id_captura

    from {{ ref('stg_camara__deputados_historico') }}

    where situacao in ('Exercício', 'Licença', 'Afastado', 'SUSPENSO', 'VACANCIA', 'FIM_MANDATO', 'SUPLENCIA')

    group by id_deputado, id_legislatura, dt_registro

),

camara as (

    select
        *,
        lag(entra) over janela as entra_anterior,
        min(dt_registro) filter (where not entra) over proximas as dt_saida,
        arg_min(descricao_saida, dt_registro) filter (where not entra) over proximas as causa_saida

    from marcos

    window
        janela as (partition by id_deputado, id_legislatura order by dt_registro),
        proximas as (
            partition by id_deputado, id_legislatura order by dt_registro rows between 1 following and unbounded following
        )

),

periodos as (

    select
        '{{ var("source_camara") }}' as fonte,
        '{{ var("source_camara") }}-' || id_deputado || '-' || id_legislatura || '-' || strftime(dt_registro, '%Y%m%d%H%M') as id_exercicio,
        cast(id_deputado as varchar) as id_na_fonte,
        '{{ var("id_type_camara") }}' as id_tipo,
        'deputado_federal' as id_cargo,
        condicao_eleitoral as condicao_na_fonte,
        id_legislatura,
        uf_sigla as uf,
        cast(dt_registro as date) as dt_inicio,
        cast(dt_saida as date) as dt_fim,
        -- o mandato da Câmara acaba com a legislatura
        cast((select l.dt_fim from {{ ref('dim_legislaturas') }} as l where l.id_legislatura = camara.id_legislatura) as date)
            as dt_mandato_fim,
        causa_saida as causa_fim,
        id_captura

    from camara

    -- uma entrada logo depois de outra entrada continua o mesmo período
    where entra and coalesce(entra_anterior, false) = false

    union all

    select
        '{{ var("source_senado") }}',
        '{{ var("source_senado") }}-' || id_exercicio,
        cast(id_senador as varchar),
        '{{ var("id_type_senado") }}',
        'senador',
        participacao,
        null,
        uf,
        dt_inicio,
        dt_fim,
        cast(dt_mandato_fim as date),
        causa_afastamento,
        id_captura

    from {{ ref('stg_senado__exercicios') }}

),

exercicios as (

    select
        p.fonte,
        p.id_exercicio,
        i.id_pessoa,
        p.id_cargo,
        t.id_territorio,
        p.condicao_na_fonte,
        p.id_legislatura,
        p.uf,
        p.dt_inicio,
        p.dt_fim,
        p.dt_mandato_fim,
        p.causa_fim,
        p.id_captura,
        cast(k.dt_captura as date) as dt_captura

    from periodos as p

    left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = p.id_captura

    left join {{ ref('stg_identity__pessoas_identificadores') }} as i
        on i.fonte = p.fonte and i.id_tipo = p.id_tipo and i.id_na_fonte = p.id_na_fonte

    left join {{ ref('dim_territorios') }} as t on t.tipo = 'uf' and t.sigla = p.uf

),

mandato_cumprido as (

    select e.id_exercicio, m.id_candidatura

    from exercicios as e

    inner join {{ ref('fct_mandatos') }} as m
        on m.id_pessoa = e.id_pessoa
        and m.id_cargo = e.id_cargo
        and e.dt_inicio between m.dt_inicio - interval 31 day and m.dt_fim_prevista

    qualify row_number() over (partition by e.id_exercicio order by m.dt_inicio desc) = 1

),

partido_informado as (

    -- o período do histórico da Câmara que contém o início do exercício
    select e.id_exercicio, arg_max(pp.id_partido, pp.dt_inicio) as id_partido

    from exercicios as e

    inner join {{ ref('fct_pessoas_partidos') }} as pp
        on pp.id_pessoa = e.id_pessoa
        and pp.base = 'historico_de_deputados'
        and pp.id_partido is not null
        and e.dt_inicio between pp.dt_inicio and pp.dt_ultimo_registro

    group by e.id_exercicio

),

partido_derivado as (

    -- o partido que a pessoa tinha no ano do início (o último registrado até lá)
    select e.id_exercicio, arg_max(pp.id_partido, pp.ano_referencia) as id_partido

    from exercicios as e

    inner join {{ ref('fct_pessoas_partidos') }} as pp
        on pp.id_pessoa = e.id_pessoa and pp.ano_referencia <= year(e.dt_inicio)

    group by e.id_exercicio

)

select
    e.*,
    mc.id_candidatura,
    coalesce(pinf.id_partido, pd.id_partido) as id_partido,
    case
        when pinf.id_partido is not null then 'informado'
        when pd.id_partido is not null then 'derivado'
    end as base_partido

from exercicios as e

left join mandato_cumprido as mc on mc.id_exercicio = e.id_exercicio

left join partido_informado as pinf on pinf.id_exercicio = e.id_exercicio

left join partido_derivado as pd on pd.id_exercicio = e.id_exercicio
