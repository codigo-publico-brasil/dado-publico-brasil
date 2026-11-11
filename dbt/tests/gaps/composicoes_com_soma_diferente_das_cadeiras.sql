{{ config(severity='warn') }}
-- Cortes em que a soma de ocupantes de um cargo não bate com as cadeiras: 513 deputados federais (Lei Complementar 78/1993)
-- e 81 senadores (CF art. 46, § 1º). Vale para as duas composições (eleita e em exercício). A diferença é medida, nunca
-- ajustada: positiva quando há mais gente do que cadeiras (por exemplo, dois períodos de exercício sobrepostos, suplente
-- em exercício enquanto o do titular ainda consta como aberto), negativa quando falta gente (exercício sem a fonte,
-- eleição não carregada). A causa está na fonte ou na cobertura; aqui só se mede.
with cadeiras as (

    select 'deputado_federal' as id_cargo, 513 as qtd_cadeiras
    union all
    select 'senador', 81

)

select
    c.dt_corte,
    c.tipo_composicao,
    c.id_cargo,
    k.qtd_cadeiras,
    sum(c.qtd_membros) as qtd_membros,
    sum(c.qtd_membros) - k.qtd_cadeiras as diferenca

from {{ ref('agg_composicoes') }} as c

inner join cadeiras as k on k.id_cargo = c.id_cargo

group by c.dt_corte, c.tipo_composicao, c.id_cargo, k.qtd_cadeiras

having sum(c.qtd_membros) <> k.qtd_cadeiras
