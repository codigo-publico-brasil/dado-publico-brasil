{{ config(severity='warn') }}
-- Tipos do catálogo que ainda não têm nenhum evento: o fato de origem não está carregado ou não gera esse tipo. Hoje:
-- diplomação, nomeação, exoneração, entrada e saída de órgão, filiação e desfiliação por data, retorno de afastamento e
-- candidatura cassada quando a fonte não traz.
select t.id_tipo_evento
from {{ ref('dim_evento_tipos') }} as t
where not exists (select 1 from {{ ref('fct_eventos') }} as e where e.id_tipo_evento = t.id_tipo_evento)
