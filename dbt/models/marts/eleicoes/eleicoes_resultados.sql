-- O que aconteceu em cada turno da eleição, candidatura a candidatura, SÓ com os arquivos do TSE (sem Câmara, Senado nem
-- identidade de pessoa). Uma linha por candidatura e turno, de todos os cargos menos vereador (candidaturas de vereador
-- são milhões; os eleitos estão em `eleitos`).
--  - `resultado` é o que o arquivo de candidaturas informa; `resultado_votacao`, o que o arquivo de votação informa. Os
--    dois podem estar vazios (em 2006 o TSE não informa quem venceu o 2º turno de presidente, nem 2010 na votação).
--  - `fl_mais_votado_no_turno` é DERIVADO dos votos, não é resultado do TSE: só existe para cargo de uma vaga (presidente,
--    governador, prefeito) e diz quem teve mais votos válidos naquele turno. Vazio onde não há votos carregados.
with votos as (

    select
        id_candidatura,
        turno,
        sum(votos_validos) as qtd_votos_validos,
        sum(votos_nominais) as qtd_votos_nominais,
        arg_max(resultado, length(coalesce(resultado, ''))) as resultado_votacao

    from {{ ref('stg_tse__votacao') }}

    group by id_candidatura, turno

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

    from {{ ref('stg_tse__candidaturas') }} as c

    inner join votos as v on v.id_candidatura = c.id_candidatura and v.turno = c.turno

    where c.cargo <> 'Vereador'

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    c.turno,
    c.ano_eleicao,
    c.uf,
    c.ue,
    c.ue_nome,
    c.cargo,
    c.numero,
    c.nome_urna,
    c.partido_sigla as partido,
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
    cast(k.dt_captura as date) as dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || c.ano_eleicao as fonte_url

from {{ ref('stg_tse__candidaturas') }} as c

left join votos as v on v.id_candidatura = c.id_candidatura and v.turno = c.turno

left join votos_da_disputa as d on d.id_candidatura = c.id_candidatura and d.turno = c.turno

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = c.id_captura

where c.cargo <> 'Vereador'
