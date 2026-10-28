{#
    Fonte do TSE já sem os marcadores de "sem valor" (#NULO, #NULO#, #NE, #NE#): todo texto passa por `tse_value`, que os troca
    por vazio, tira espaços repetidos e trata o vazio como vazio. O raw continua espelhando a fonte; a limpeza vale do staging em
    diante. Só as colunas que o modelo usa são calculadas (o DuckDB descarta o resto). Para tabelas do raw que podem ainda não
    ter sido carregadas (cargas pesadas e opcionais), passe `columns`: sem a tabela, volta a tabela vazia do `raw_or_empty`.
#}
{% macro tse_source(table, columns=none) %}
    {%- set relation = source('tse', table) -%}
    {%- if not execute -%}
        {{ relation }}
    {%- elif columns is not none and adapter.get_relation(database=relation.database, schema=relation.schema, identifier=relation.identifier) is none -%}
        {{ raw_or_empty('tse', table, columns) }}
    {%- else -%}
        (select
        {%- for column in adapter.get_columns_in_relation(relation) %}
            {% if column.is_string() and not column.name.startswith('_') -%}
                tse_value({{ adapter.quote(column.name) }}) as {{ adapter.quote(column.name) }}
            {%- else -%}
                {{ adapter.quote(column.name) }}
            {%- endif -%}{{ ',' if not loop.last }}
        {%- endfor %}
        from {{ relation }})
    {%- endif -%}
{% endmacro %}
