-- Erro se, numa partição (ano ou mês) de arquivo que é a foto completa (`meta.escrita: replace_partition`), o raw tem
-- linhas diferentes das que a carga da captura vigente registrou (`qtd_linhas` em `metadata.fontes_verificacoes`):
-- sobra de versão anterior (a votação de 2022 chegou a ter o dobro) ou perda. Só confere o que já foi carregado.
{% set tabelas = [] %}
{% if execute %}
    {% for s in graph.sources.values() if s.meta.get('escrita') == 'replace_partition' and adapter.get_relation(s.database, s.schema, s.identifier) %}
        {% do tabelas.append(s) %}
    {% endfor %}
{% endif %}
with carga as (

    select
        fonte,
        dataset,
        particao,
        qtd_linhas as linhas_carregadas

    from {{ source('metadata', 'fontes_verificacoes') }}

    where verificacao = 'carga'

    qualify row_number() over (partition by fonte, dataset, particao order by id_verificacao desc) = 1

),

raw_por_particao as (
{% for s in tabelas %}
    select '{{ s.source_name }}' as fonte, '{{ s.name }}' as dataset, c.particao, count(*) as linhas_raw
    from {{ s.relation_name }} as r
    inner join {{ source('metadata', 'capturas') }} as c on c.id_captura = r._source_file_id
    group by c.particao
    {% if not loop.last %}union all{% endif %}
{% endfor %}
{% if not tabelas %}select cast(null as varchar) as fonte, cast(null as varchar) as dataset, cast(null as integer) as particao, cast(null as bigint) as linhas_raw where false{% endif %}
)

select r.fonte, r.dataset, r.particao, r.linhas_raw, c.linhas_carregadas

from raw_por_particao as r

inner join carga as c
    on c.fonte = r.fonte and c.dataset = r.dataset and c.particao is not distinct from r.particao

where r.linhas_raw <> c.linhas_carregadas
