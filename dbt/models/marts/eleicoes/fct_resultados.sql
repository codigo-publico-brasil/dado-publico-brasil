-- O que aconteceu em cada turno da eleição, candidatura a candidatura, SÓ com arquivos do TSE. Uma linha por candidatura
-- e turno, de todos os cargos (inclusive vereador).
--  - `resultado` é o que o arquivo de candidaturas informa; `resultado_votacao`, o que o arquivo de votação informa. Os
--    dois podem estar vazios (em 2006 o TSE não informa quem venceu o 2º turno de presidente, nem 2010 na votação).
--  - `fl_mais_votado_no_turno` é DERIVADO dos votos, não é resultado do TSE: só existe para cargo de uma vaga (presidente,
--    governador, prefeito) e diz quem teve mais votos válidos naquele turno. Vazio onde não há votos carregados.
with votos as (

    select
        id_candidatura,
        turno,
        sum(votos_validos) as qtd_votos_validos,
        if(sum(votos_nominais) = 0 and sum(votos_validos) > 0, null, sum(votos_nominais)) as qtd_votos_nominais,
        arg_max(resultado, length(coalesce(resultado, ''))) as resultado_votacao

    from {{ ref('stg_tse__votacao') }}

    group by id_candidatura, turno

),

turnos as (

    -- o que a candidatura informa, mais os turnos que só a votação traz (em 2006 o arquivo de candidaturas não tem o 2º turno
    -- de presidente, mas a votação tem); a candidatura precisa existir
    select id_candidatura, turno, situacao_candidatura, resultado, ano_eleicao, ue, cargo, id_captura

    from {{ ref('stg_tse__candidaturas') }}

    union all

    select
        v.id_candidatura, v.turno, cast(null as varchar), cast(null as varchar), c.ano_eleicao, c.ue, c.cargo, c.id_captura

    from (select distinct id_candidatura, turno from votos) as v

    inner join (
        select distinct on (id_candidatura) id_candidatura, ano_eleicao, ue, cargo, id_captura
        from {{ ref('stg_tse__candidaturas') }}
        order by id_candidatura, turno
    ) as c on c.id_candidatura = v.id_candidatura

    where not exists (
        select 1 from {{ ref('stg_tse__candidaturas') }} as x where x.id_candidatura = v.id_candidatura and x.turno = v.turno
    )

),

votos_da_disputa as (

    -- votos válidos de todos os candidatos da mesma disputa (ano, turno, unidade e cargo), para o percentual e o 1º lugar
    select
        c.id_candidatura,
        c.turno,
        v.qtd_votos_validos,
        sum(v.qtd_votos_validos) over (partition by c.ano_eleicao, c.turno, c.ue, c.cargo) as total_votos_validos,
        row_number() over (
            partition by c.ano_eleicao, c.turno, c.ue, c.cargo order by v.qtd_votos_validos desc nulls last
        ) as posicao

    from turnos as c

    inner join votos as v on v.id_candidatura = c.id_candidatura and v.turno = c.turno

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    c.turno,
    c.situacao_candidatura,
    c.resultado,
    v.resultado_votacao,
    cast(v.qtd_votos_validos as bigint) as qtd_votos_validos,
    cast(v.qtd_votos_nominais as bigint) as qtd_votos_nominais,
    cast(round(100.0 * d.qtd_votos_validos / nullif(d.total_votos_validos, 0), 2) as decimal(5, 2)) as percentual_votos_validos,
    if(
        c.cargo in ('Presidente', 'Governador', 'Prefeito') and d.qtd_votos_validos is not null,
        d.posicao = 1 and d.qtd_votos_validos > 0,
        null
    ) as fl_mais_votado_no_turno,
    c.id_captura

from turnos as c

left join votos as v on v.id_candidatura = c.id_candidatura and v.turno = c.turno

left join votos_da_disputa as d on d.id_candidatura = c.id_candidatura and d.turno = c.turno
