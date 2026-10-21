select
    '{{ var("source_camara") }}' as fonte,
    orgao_id,
    sigla,
    apelido,
    nome,
    tipo_orgao as tipo,
    inicio,
    instalado_em,
    fim,
    situacao,
    casa,
    fonte_url

from {{ ref('stg_camara__orgaos') }}
