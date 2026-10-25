{#
    Fonte do raw que pode ainda não ter sido carregada: devolve a própria fonte quando a tabela existe e, quando não existe,
    uma tabela vazia com as mesmas colunas (texto) e `_source_file_id`. Serve às cargas pesadas e opcionais (por exemplo, a
    prestação de contas dos candidatos): o dbt segue rodando e os marts mostram total vazio, e não zero, até a carga vir.
#}
{% macro raw_or_empty(source_name, table, columns) %}
    {%- set relation = source(source_name, table) -%}
    {%- if execute and adapter.get_relation(database=relation.database, schema=relation.schema, identifier=relation.identifier) is none -%}
        (select {% for column in columns %}cast(null as varchar) as {{ column }}, {% endfor %}cast(null as bigint) as _source_file_id where false)
    {%- else -%}
        {{ relation }}
    {%- endif -%}
{% endmacro %}
