-- As fotos oficiais que o TSE publica das candidaturas das eleições gerais: uma linha por arquivo de imagem dentro de cada
-- pacote por UF. Só lista (o raw guarda o nome e o tamanho; o pacote original está no landing). O nome do arquivo é
-- `F<UF><SQ_CANDIDATO>_div.jpg` (ou `.jpeg`). Pacote não carregado vale por vazio (as fotos são carga opcional).
with pacotes as (

{% set ufs = ['br', 'ac', 'al', 'am', 'ap', 'ba', 'ce', 'df', 'es', 'go', 'ma', 'mg', 'ms', 'mt', 'pa', 'pb', 'pe', 'pi', 'pr', 'rj', 'rn', 'ro', 'rr', 'rs', 'sc', 'se', 'sp', 'to'] %}
{% for uf in ufs %}
    select '{{ uf | upper }}' as pacote_uf, member, size, _source_file_id as id_captura
    from {{ raw_or_empty('tse', 'fotos_' ~ uf, ['member', 'size']) }}
{% if not loop.last %}
    union all
{% endif %}
{% endfor %}

)

select
    k.ano as ano_eleicao,
    p.pacote_uf,
    try_cast(regexp_extract(p.member, '^F[A-Z]{2}([0-9]+)_div', 1) as bigint) as sq_candidato,
    p.member as arquivo,
    cast(p.size as bigint) as tamanho_bytes,
    p.id_captura

from pacotes as p

inner join {{ ref('stg_metadata__captures') }} as k on k.id_captura = p.id_captura
