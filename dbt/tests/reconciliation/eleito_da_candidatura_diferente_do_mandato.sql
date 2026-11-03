-- A candidatura com `base_eleicao` (fct_candidaturas) e o mandato (fct_mandatos) são o mesmo conjunto: é o que permite ao
-- aplicativo ler o eleito (inclusive o derivado) só de fct_candidaturas. O esperado é nenhuma linha.
select coalesce(c.id_candidatura, m.id_candidatura) as id_candidatura, c.base_eleicao, m.base_eleicao as base_mandato
from (select id_candidatura, base_eleicao from {{ ref('fct_candidaturas') }} where base_eleicao is not null) as c
full outer join {{ ref('fct_mandatos') }} as m on m.id_candidatura = c.id_candidatura
where c.id_candidatura is null or m.id_candidatura is null or c.base_eleicao is distinct from m.base_eleicao
