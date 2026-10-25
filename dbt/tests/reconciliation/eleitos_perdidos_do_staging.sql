-- Conciliação: todo eleito (resultado "eleito", dos quatro cargos) do staging das candidaturas tem uma linha em `eleitos`.
-- Linhas aqui são eleitos perdidos entre o staging e o mart.
select s.id_candidatura

from {{ ref('stg_tse__candidaturas') }} as s

where s.resultado like 'Eleito%'
    and s.cargo in ('Presidente', 'Governador', 'Senador', 'Deputado federal')
    and not exists (select 1 from {{ ref('eleitos') }} as e where e.id_candidatura = s.id_candidatura)
