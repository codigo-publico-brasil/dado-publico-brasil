{{ config(severity='warn') }}
-- Presidente, governador ou senador eleito sem o vice (1) ou os dois suplentes (senador) que a chapa deveria ter. A lacuna
-- é da fonte ou da ligação por número; nada é inferido.
select
    e.id_candidatura,
    e.cargo,
    e.ano_eleicao,
    e.ue,
    count(c.id_candidatura) as qtd_integrantes

from {{ ref('eleitos') }} as e

left join {{ ref('eleitos_chapas') }} as c on c.id_candidatura_titular = e.id_candidatura

where e.cargo in ('Presidente', 'Governador', 'Senador')

group by all

having count(c.id_candidatura) <> if(e.cargo = 'Senador', 2, 1)
