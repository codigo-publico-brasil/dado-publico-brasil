{#
    Colunas de auditoria do staging de fonte (ADR 0035). Fecha o modelo: recebe a CTE `base`, que traz `id_captura` (o
    `_source_file_id` do raw), e devolve as colunas dela mais, ao final, `fonte`, `id_captura`, `dt_captura`, `url_fonte` e
    `sha256_captura`, ligadas a `stg_metadata__capturas` pela chave da captura (única: a junção não multiplica linhas).
    A fonte vem do nome do modelo (`stg_<fonte>__<tabela>`). A junção é com a tabela de capturas (milhares de linhas), e
    é left: linha sem captura aparece com as colunas vazias, e o teste `relationships` do YAML acusa.
#}
{% macro colunas_auditoria(base='renamed') %}
select
    b.* exclude (id_captura),
    '{{ this.name.split("__")[0][4:] }}' as fonte,
    b.id_captura,
    k.dt_captura,
    k.url as url_fonte,
    k.sha256 as sha256_captura

from {{ base }} as b

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = b.id_captura
{% endmacro %}
