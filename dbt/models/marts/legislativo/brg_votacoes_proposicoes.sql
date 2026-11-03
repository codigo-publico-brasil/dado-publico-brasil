-- Que proposição (ou matéria) cada votação decidiu, uma linha por votação e proposição, com o papel. Troca o texto
-- "PL 1/2020, PL 2/2020" de fct_votacoes por linhas que ligam a fct_proposicoes.
--  - Câmara: afetada (a votação mudou a situação da proposição) ou objeto (foi o assunto votado), como a Câmara informa.
--  - Senado: a matéria da votação (uma por votação), papel 'materia'.
-- Votação sem proposição na fonte não tem linha. A proposição pode não estar carregada em fct_proposicoes (o teste de
-- aviso mede quantas).
select
    '{{ var("source_camara") }}' as fonte,
    vp.id_votacao,
    cast(vp.id_proposicao as varchar) as id_proposicao,
    vp.papel,
    vp.id_captura,
    cast(vp.dt_captura as date) as dt_captura

from {{ ref('int_votacoes_proposicoes_unidas') }} as vp

union all

select
    '{{ var("source_senado") }}',
    cast(v.id_votacao as varchar),
    cast(v.id_materia as varchar),
    'materia',
    v.id_captura,
    cast(v.dt_captura as date)

from {{ ref('stg_senado__votacoes') }} as v

where v.id_materia is not null
