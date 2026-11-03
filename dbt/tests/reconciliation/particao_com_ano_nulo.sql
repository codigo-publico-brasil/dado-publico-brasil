-- Toda `meta.particao` declarada (expressão SQL do ano, ADR 0035) precisa ser válida e nunca dar nulo: o export falha com ano nulo.
-- Só confere o que já foi construído. Expressão inválida quebra a consulta, e o teste falha do mesmo jeito.
{% set tabelas = [] %}
{% if execute %}
    {% for n in graph.nodes.values() if n.resource_type == 'model' and n.config.meta.get('particao') and adapter.get_relation(n.database, n.schema, n.alias) %}
        {% do tabelas.append(n) %}
    {% endfor %}
{% endif %}
{% for n in tabelas %}
select '{{ n.name }}' as modelo, count(*) as linhas_sem_ano
from {{ n.relation_name }}
where ({{ n.config.meta.get('particao') }}) is null
having count(*) > 0
{% if not loop.last %}union all{% endif %}
{% endfor %}
{% if not tabelas %}select cast(null as varchar) as modelo, 0 as linhas_sem_ano where false{% endif %}
