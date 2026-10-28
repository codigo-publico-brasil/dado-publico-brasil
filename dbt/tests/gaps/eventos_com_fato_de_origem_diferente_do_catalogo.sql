-- Erro se um evento nasceu de um fato diferente do que o catálogo core.evento_tipos declara para o tipo.
select e.id_tipo_evento, e.fato_origem, t.fato_origem as fato_origem_do_catalogo, count(*) as qtd
from {{ ref('fatos_eventos') }} as e
inner join {{ ref('evento_tipos') }} as t on t.id_tipo_evento = e.id_tipo_evento
where e.fato_origem <> t.fato_origem
group by 1, 2, 3
