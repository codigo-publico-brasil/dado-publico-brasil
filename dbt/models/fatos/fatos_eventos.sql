-- A linha do tempo da pessoa: uma linha por evento, DERIVADA dos fatos tipados (a verdade está neles; aqui não há texto livre).
-- O tipo vem do catálogo fechado core.evento_tipos e `fato_origem` diz de qual fato a linha nasceu (um teste confere o par).
-- `ano_evento` sempre existe; `dt_evento` só quando a fonte dá o dia (eleição e candidatura só têm o ano).
-- Tipos sem fato carregado (diplomação, nomeação, exoneração, entrada e saída de órgão, filiação e desfiliação por data,
-- retorno de afastamento) não têm linha ainda: o teste de cobertura lista quais.
with candidaturas as (

    select
        c.id_candidatura,
        c.id_pessoa,
        c.id_disputa,
        c.id_partido,
        c.situacao_candidatura,
        c.resultado,
        c.qtd_turnos,
        a.ano_eleicao,
        d.id_cargo,
        d.id_territorio,
        c.id_captura

    from {{ ref('fatos_candidaturas') }} as c

    inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
        on a.id_candidatura = c.id_candidatura

    left join {{ ref('disputas') }} as d on d.id_disputa = c.id_disputa

    where c.id_pessoa is not null

),

falecimentos as (

    select id_pessoa, dt_falecimento from {{ ref('int_pessoas_unidas_cadastro') }} where dt_falecimento is not null

    union

    select id_pessoa, dt_falecimento from {{ ref('int_pessoas_senado_unidas') }} where dt_falecimento is not null

),

eventos as (

    -- vida
    select
        id_pessoa,
        'nascimento' as id_tipo_evento,
        'pessoas' as fato_origem,
        cast(id_pessoa as varchar) as id_fato_origem,
        year(dt_nascimento) as ano_evento,
        if(
            fonte_dt_nascimento = '{{ var("source_tse") }}' and month(dt_nascimento) = 1 and day(dt_nascimento) = 1,
            cast(null as date),
            dt_nascimento
        ) as dt_evento,
        cast(null as varchar) as id_disputa,
        cast(null as varchar) as id_cargo,
        cast(null as varchar) as id_territorio,
        cast(null as integer) as id_partido,
        'informado' as base,
        cast(null as bigint) as id_captura

    from {{ ref('core_pessoas') }}

    where dt_nascimento is not null

    union all

    select
        id_pessoa, 'falecimento', 'pessoas', cast(id_pessoa as varchar), year(dt_falecimento), dt_falecimento,
        null, null, null, null, 'informado', null

    from falecimentos

    -- eleição
    union all

    select
        id_pessoa, 'candidatura_registrada', 'candidaturas', id_candidatura, ano_eleicao, cast(null as date),
        id_disputa, id_cargo, id_territorio, id_partido, 'informado', id_captura

    from candidaturas

    union all

    select
        id_pessoa,
        case
            when situacao_candidatura in ('Deferido', 'Apto') then 'candidatura_deferida'
            when situacao_candidatura like 'Indeferido%' then 'candidatura_indeferida'
            when situacao_candidatura like 'Cassa%' then 'candidatura_cassada'
        end,
        'candidaturas', id_candidatura, ano_eleicao, cast(null as date), id_disputa, id_cargo, id_territorio, null,
        'informado', id_captura

    from candidaturas

    where situacao_candidatura in ('Deferido', 'Apto')
        or situacao_candidatura like 'Indeferido%'
        or situacao_candidatura like 'Cassa%'

    union all

    select
        id_pessoa,
        case when resultado like 'N_o eleito%' then 'nao_eleito' when resultado = 'Suplente' then 'suplente_eleito' end,
        'candidaturas', id_candidatura, ano_eleicao, cast(null as date), id_disputa, id_cargo, id_territorio,
        if(resultado = 'Suplente', id_partido, null), 'informado', id_captura

    from candidaturas

    where resultado like 'N_o eleito%' or resultado = 'Suplente'

    union all

    select
        id_pessoa, 'segundo_turno_disputado', 'candidaturas', id_candidatura, ano_eleicao, cast(null as date),
        id_disputa, id_cargo, id_territorio, null, 'informado', id_captura

    from candidaturas

    where qtd_turnos = 2

    union all

    select
        m.id_pessoa, 'eleito', 'mandatos', m.id_candidatura, a.ano_eleicao, cast(null as date),
        m.id_disputa, m.id_cargo, m.id_territorio, m.id_partido, m.base_eleicao, m.id_captura

    from {{ ref('fatos_mandatos') }} as m

    inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
        on a.id_candidatura = m.id_candidatura

    where m.id_pessoa is not null

    -- mandato
    union all

    select
        id_pessoa, 'posse', 'mandatos', id_candidatura, year(dt_inicio), dt_inicio,
        id_disputa, id_cargo, id_territorio, id_partido, base_dt_inicio, id_captura

    from {{ ref('fatos_mandatos') }}

    where id_pessoa is not null and dt_inicio is not null

    union all

    select
        id_pessoa, 'assuncao_por_suplencia', 'exercicios', id_exercicio, year(dt_inicio), dt_inicio,
        null, id_cargo, null, null, 'informado', id_captura

    from {{ ref('fatos_exercicios') }}

    where id_pessoa is not null
        and (lower(condicao_na_fonte) like '%suplente%' or lower(condicao_na_fonte) = 'efetivado')

    union all

    select
        id_pessoa,
        case
            when lower(causa_fim) like '%término%' then 'termino_de_mandato'
            when lower(causa_fim) like '%renúncia%' then 'renuncia'
            when lower(causa_fim) like '%cassa%' then 'cassacao_de_mandato'
            else 'afastamento'
        end,
        'exercicios', id_exercicio, year(dt_fim), dt_fim, null, id_cargo, null, null, 'informado', id_captura

    from {{ ref('fatos_exercicios') }}

    where id_pessoa is not null
        and dt_fim is not null
        and lower(coalesce(causa_fim, '')) not like '%retorno do titular%'

    -- partido
    union all

    select
        id_pessoa, 'troca_de_partido', 'pessoas_partidos', id_pessoa_partido, ano_referencia, dt_inicio,
        null, null, null, id_partido, 'informado', id_captura

    from (
        select
            *,
            lag(id_partido) over (
                partition by id_pessoa order by ano_referencia, coalesce(dt_inicio, date '1900-01-01'), fonte
            ) as id_partido_anterior

        from {{ ref('fatos_pessoas_partidos') }}

        where id_pessoa is not null and id_partido is not null
    )

    where id_partido_anterior is not null and id_partido_anterior <> id_partido

)

select
    id_tipo_evento || ':' || fato_origem || ':' || id_fato_origem as id_evento,
    *

from eventos
