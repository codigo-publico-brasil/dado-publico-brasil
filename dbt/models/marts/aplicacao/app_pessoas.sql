-- A ficha cadastral de cada pessoa do projeto (quem já foi eleito), com a foto. Join puro sobre os marts: a regra (o cadastro da
-- Câmara e do Senado vale primeiro; o que falta vem da candidatura mais recente do TSE que o informa) está em dim_pessoas.
-- Contato institucional, redes, site e falecimento só existem no cadastro das casas e ficam vazios para os demais.
-- `foto_caminho` é a foto oficial do TSE (coleção arq_fotos do lake); `foto_url` é a da Câmara ou do Senado.
-- `fonte_url` vem de metadata.capturas, parte do contrato do lake: o app obtém o mesmo por `id_captura`.
with captura_cadastro as (

    -- a captura mais recente do cadastro de cada casa (deputados e senadores)
    select fonte, arg_max(url, dt_captura) as url, cast(max(dt_captura) as date) as dt_captura

    from {{ source('metadata', 'capturas') }}

    where dataset in ('deputados', 'senadores')

    group by fonte

)

select
    p.id_pessoa,
    p.nome_publico as nome,
    p.nome_civil,
    p.nome_social,
    p.genero,
    p.dt_nascimento,
    c.dt_falecimento,
    c.municipio_nascimento,
    p.uf_nascimento,
    p.escolaridade,
    p.estado_civil,
    p.profissoes,
    c.situacao_atual,
    c.email_institucional,
    c.telefone_institucional,
    c.gabinete_endereco,
    c.pagina_url,
    c.site_url,
    c.rede_social_url,
    p.foto_caminho,
    c.foto_url,
    c.fontes,
    coalesce(cc.url, ct.url) as fonte_url,
    coalesce(cc.dt_captura, cast(ct.dt_captura as date)) as dt_captura

from {{ ref('dim_pessoas') }} as p

left join {{ ref('dim_pessoas_cadastro') }} as c on c.id_pessoa = p.id_pessoa

left join captura_cadastro as cc on cc.fonte = c.fonte

left join {{ source('metadata', 'capturas') }} as ct on ct.id_captura = p.id_captura_tse
