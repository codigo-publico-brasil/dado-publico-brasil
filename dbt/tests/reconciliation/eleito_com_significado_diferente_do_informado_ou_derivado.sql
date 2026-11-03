-- `fl_eleito` de fct_candidaturas é o eleito completo: o que o TSE informa (`fl_eleito_informado`) ou o que se deriva dos
-- votos (`base_eleicao`), e coincide com a existência da candidatura em fct_mandatos. O esperado é nenhuma linha.
select c.id_candidatura, c.fl_eleito, c.fl_eleito_informado, c.base_eleicao, m.id_candidatura is not null as tem_mandato
from {{ ref('fct_candidaturas') }} as c
left join (select distinct id_candidatura from {{ ref('fct_mandatos') }}) as m on m.id_candidatura = c.id_candidatura
where c.fl_eleito is distinct from (c.fl_eleito_informado or c.base_eleicao is not null)
   or coalesce(c.fl_eleito, false) <> (m.id_candidatura is not null)
