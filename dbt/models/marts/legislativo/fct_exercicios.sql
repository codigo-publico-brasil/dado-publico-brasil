-- Cada período em que alguém exerceu de fato um mandato federal, como a fonte oficial publica (nada derivado de regra):
--  - Câmara: o histórico do deputado é uma sequência de entradas e saídas; o período vai de uma entrada em exercício
--    (posse, reassunção, suplente que assume) até a primeira saída seguinte (licença, vacância, fim de mandato).
--  - Senado: os períodos de exercício já vêm prontos, de titular e de suplentes.
-- Sem fim quando o período está em curso. Vereador, prefeito, governador e presidente não entram: não há fonte oficial
-- de exercício carregada para eles (o mandato deles está em fct_mandatos).
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

)

select
    p.fonte,
    p.id_exercicio,
    i.id_pessoa,
    p.id_cargo,
    p.condicao_na_fonte,
    p.id_legislatura,
    p.uf,
    p.dt_inicio,
    p.dt_fim,
    p.dt_mandato_fim,
    p.causa_fim,
    p.id_captura

from periodos as p

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = p.fonte and i.id_tipo = p.id_tipo and i.id_na_fonte = p.id_na_fonte
