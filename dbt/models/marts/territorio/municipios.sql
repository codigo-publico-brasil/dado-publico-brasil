-- Municípios do IBGE: a dimensão territorial da plataforma (código oficial, UF e região).
select
    'ibge' as fonte,
    m.id_municipio,
    m.nome,
    m.uf,
    m.uf_nome,
    m.regiao_sigla,
    m.regiao_nome,
    m.regiao_imediata,
    m.regiao_intermediaria,
    lower(strip_accents(m.nome)) as nome_busca,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_ibge__municipios') }} as m

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = m.id_captura
