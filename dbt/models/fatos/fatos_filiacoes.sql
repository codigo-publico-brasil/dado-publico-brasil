-- Os períodos em que cada deputado federal aparece em um partido, como o histórico da Câmara registra (a Câmara só publica o
-- partido enquanto a pessoa tem registro de mandato). Um período é uma sequência de registros datados do mesmo partido;
-- `dt_inicio` é o primeiro registro com o partido e `dt_ultimo_registro` o último, sem dizer que a filiação acabou ali:
-- o que se sabe é só que o partido seguinte aparece depois (`fl_ultimo_partido_registrado` marca o partido do registro mais recente, não o partido de hoje).
-- Troca de partido = dois períodos seguidos da mesma pessoa. O registro sem situação (nome e partido no início da
-- legislatura) tem data fora do período e não entra. A filiação do TSE fica fora até a decisão de LGPD (#38).
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

)

select
    '{{ var("source_camara") }}' as fonte,
    '{{ var("source_camara") }}-' || p.id_deputado || '-' || strftime(p.dt_inicio, '%Y%m%d%H%M') as id_filiacao,
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
    cast(p.dt_inicio as date) as dt_inicio,
    cast(p.dt_ultimo_registro as date) as dt_ultimo_registro,
    p.dt_ultimo_registro = max(p.dt_ultimo_registro) over (partition by p.id_deputado) as fl_ultimo_partido_registrado,
    p.id_captura

from periodos as p

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(p.id_deputado as varchar)
