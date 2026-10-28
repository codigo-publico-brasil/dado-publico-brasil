-- O partido de cada pessoa em cada momento, de fontes oficiais (ADR 0032):
--  - camara: períodos em que o deputado aparece em um partido no histórico da Câmara (a Câmara só publica o partido
--    enquanto há registro de mandato). Um período é uma sequência de registros datados do mesmo partido; dt_inicio é o
--    primeiro registro e dt_ultimo_registro o último, sem afirmar que a filiação acabou ali.
--  - camara/senado a partir dos votos: o partido que o parlamentar tinha em cada voto, só para quem não tem histórico de
--    deputado (senadores e deputados sem histórico); marcado em `base`.
--  - camara a partir do registro de início da legislatura: o partido no início de cada legislatura, para quem não tem
--    períodos no histórico (deputados anteriores ao histórico detalhado).
--  - tse: o partido pelo qual a pessoa concorreu em cada eleição (uma linha por candidatura de quem tem pessoa). Cobre quem
--    nunca esteve na Câmara (vereadores, prefeitos, governadores...). É o partido da candidatura, não a data de filiação.
-- Troca de partido = dois momentos seguidos da mesma pessoa com partidos diferentes. A filiação partidária por data (arquivo
-- de filiados do TSE) NÃO é carregada: ver a base legal em docs/03-consultar/05-lgpd-dados-pessoais.md.
with registros as (

    select
        id_deputado,
        dt_registro,
        partido_sigla,
        upper(replace(partido_sigla, ' ', '')) as sigla_chave,
        id_captura,
        lag(upper(replace(partido_sigla, ' ', ''))) over (partition by id_deputado order by dt_registro) as sigla_anterior

    from {{ ref('stg_camara__deputados_historico') }}

    where coalesce(situacao, '') <> '' and partido_sigla is not null

),

periodos as (

    select
        id_deputado,
        arg_min(partido_sigla, dt_registro) as partido_na_fonte,
        any_value(sigla_chave) as sigla_chave,
        min(dt_registro) as dt_inicio,
        max(dt_registro) as dt_ultimo_registro,
        max(id_captura) as id_captura

    from (
        select
            *,
            sum(coalesce(sigla_chave is distinct from sigla_anterior, true)::int)
                over (partition by id_deputado order by dt_registro) as seq
        from registros
    )

    group by id_deputado, seq

),

siglas as (

    select id_partido, upper(replace(sigla_na_fonte, ' ', '')) as sigla_chave, ano_inicio, ano_fim

    from {{ ref('partidos_siglas') }}

),

votos_sequencia as (

    select
        fonte,
        id_pessoa,
        partido_sigla,
        dt_voto,
        id_captura,
        upper(replace(partido_sigla, ' ', '')) as sigla_chave,
        lag(upper(replace(partido_sigla, ' ', ''))) over (partition by fonte, id_pessoa order by dt_voto) as sigla_anterior

    from {{ ref('int_votacoes_votos_ligados') }}

    where partido_sigla is not null and dt_voto is not null

),

votos_ilhas as (

    -- o partido que o parlamentar tinha em cada voto (Câmara e Senado); vale para quem não tem histórico de deputado
    select
        *,
        sum((sigla_chave is distinct from sigla_anterior)::int) over (partition by fonte, id_pessoa order by dt_voto) as seq

    from votos_sequencia

),

votos_periodos as (

    select
        fonte,
        id_pessoa,
        arg_min(partido_sigla, dt_voto) as partido_na_fonte,
        any_value(sigla_chave) as sigla_chave,
        min(dt_voto) as dt_inicio,
        max(dt_voto) as dt_ultimo_registro,
        max(id_captura) as id_captura

    from votos_ilhas

    group by fonte, id_pessoa, seq

),

todos as (

select
    '{{ var("source_camara") }}' as fonte,
    'historico_de_deputados' as base,
    '{{ var("source_camara") }}-' || p.id_deputado || '-' || strftime(p.dt_inicio, '%Y%m%d%H%M') as id_pessoa_partido,
    i.id_pessoa,
    -- a sigla pode ser de dois partidos (PL, PSD): vale o de período mais próximo do ano do registro
    (
        select s.id_partido
        from siglas as s
        where s.sigla_chave = p.sigla_chave
        order by greatest(s.ano_inicio - year(p.dt_inicio), year(p.dt_inicio) - s.ano_fim, 0)
        limit 1
    ) as id_partido,
    p.partido_na_fonte,
    year(p.dt_inicio) as ano_referencia,
    cast(p.dt_inicio as date) as dt_inicio,
    cast(p.dt_ultimo_registro as date) as dt_ultimo_registro,
    cast(null as varchar) as id_candidatura,
    p.id_captura

from periodos as p

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(p.id_deputado as varchar)

union all

select
    v.fonte,
    'votos',
    v.fonte || '-voto-' || v.id_pessoa || '-' || strftime(v.dt_inicio, '%Y%m%d'),
    v.id_pessoa,
    (
        select s.id_partido
        from siglas as s
        where s.sigla_chave = v.sigla_chave
        order by greatest(s.ano_inicio - year(v.dt_inicio), year(v.dt_inicio) - s.ano_fim, 0)
        limit 1
    ),
    v.partido_na_fonte,
    year(v.dt_inicio),
    cast(v.dt_inicio as date),
    cast(v.dt_ultimo_registro as date),
    cast(null as varchar),
    v.id_captura

from votos_periodos as v

where not exists (
    select 1 from periodos as p
    inner join {{ ref('stg_identity__pessoa_identificadores') }} as i2
        on i2.fonte = '{{ var("source_camara") }}' and i2.id_na_fonte = cast(p.id_deputado as varchar)
    where i2.id_pessoa = v.id_pessoa
)

union all

select
    '{{ var("source_camara") }}',
    'inicio_da_legislatura',
    '{{ var("source_camara") }}-leg-' || l.id_deputado || '-' || l.id_legislatura,
    i.id_pessoa,
    (
        select s.id_partido
        from siglas as s
        where s.sigla_chave = upper(replace(l.partido_sigla, ' ', ''))
        order by greatest(s.ano_inicio - year(l.dt_inicio), year(l.dt_inicio) - s.ano_fim, 0)
        limit 1
    ),
    l.partido_sigla,
    year(l.dt_inicio),
    cast(l.dt_inicio as date),
    cast(null as date),
    cast(null as varchar),
    l.id_captura

from (
    -- o registro sem situação do histórico traz o partido no início da legislatura; sua data não é a da legislatura
    select distinct on (h.id_deputado, h.id_legislatura)
        h.id_deputado, h.id_legislatura, h.partido_sigla, g.dt_inicio, h.id_captura
    from {{ ref('stg_camara__deputados_historico') }} as h
    inner join {{ ref('stg_camara__legislaturas') }} as g on g.id_legislatura = h.id_legislatura
    where coalesce(h.situacao, '') = '' and h.partido_sigla is not null
    order by h.id_deputado, h.id_legislatura, h.dt_registro desc
) as l

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(l.id_deputado as varchar)

where not exists (select 1 from periodos as p where p.id_deputado = l.id_deputado)

union all

select
    '{{ var("source_tse") }}',
    'candidatura',
    '{{ var("source_tse") }}-' || c.id_candidatura,
    c.id_pessoa,
    c.id_partido,
    c.partido,
    a.ano_eleicao,
    cast(null as date),
    cast(null as date),
    c.id_candidatura,
    c.id_captura

from {{ ref('fatos_candidaturas') }} as c

inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
    on a.id_candidatura = c.id_candidatura

where c.id_pessoa is not null

)

select
    *,
    row_number() over (
        partition by id_pessoa order by ano_referencia desc, coalesce(dt_ultimo_registro, date '1900-01-01') desc, fonte
    ) = 1 as fl_mais_recente

from todos
