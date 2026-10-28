{{ config(severity='warn') }}
-- Cortes em que a composição em exercício tem mais gente do que cadeiras: 513 deputados federais (Lei Complementar 78/1993)
-- e 81 senadores (CF art. 46, § 1º). Acontece quando dois períodos de exercício da fonte se sobrepõem (suplente em exercício
-- enquanto o período do titular ainda consta como aberto). A causa está na fonte e não é corrigida aqui.
select dt_corte, id_cargo, sum(qtd_membros) as qtd_membros
from {{ ref('analise_composicoes') }}
where tipo_composicao = 'exercicio'
group by dt_corte, id_cargo
having (id_cargo = 'deputado_federal' and sum(qtd_membros) > 513)
    or (id_cargo = 'senador' and sum(qtd_membros) > 81)
