with cadastro as (

    select
        id_pessoa, fonte, nome, nome_civil, sexo, dt_nascimento, dt_falecimento, municipio_nascimento,
        uf_nascimento, foto_url, rede_social_url, site_url, escolaridade, situacao_atual, condicao_eleitoral,
        email_institucional, telefone_institucional, gabinete_endereco, pagina_url, id_captura, dt_captura
    from {{ ref('int_pessoas_unidas_cadastro') }}

    union all

    select
        id_pessoa, fonte, nome, nome_civil, sexo, dt_nascimento, dt_falecimento, municipio_nascimento,
        uf_nascimento, foto_url, rede_social_url, site_url, escolaridade, situacao_atual, condicao_eleitoral,
        email_institucional, telefone_institucional, gabinete_endereco, pagina_url, id_captura, dt_captura
    from {{ ref('int_pessoas_senado_unidas') }}

),

uma_por_pessoa as (

    -- depois da fusão das chaves, a pessoa pode estar nas duas casas: os dados da Câmara vencem
    select
        *,
        string_agg(fonte, ', ' order by fonte) over (partition by id_pessoa) as fontes

    from cadastro

    qualify row_number() over (partition by id_pessoa order by if(fonte = '{{ var("source_camara") }}', 0, 1)) = 1

)

select
    p.id_pessoa,
    p.fonte,
    p.fontes,
    p.nome,
    p.nome_civil,
    lower(strip_accents(p.nome)) as nome_ordem,
    lower(strip_accents(p.nome || ' ' || coalesce(p.nome_civil, ''))) as nome_busca,
    p.sexo,
    p.dt_nascimento,
    p.dt_falecimento,
    p.municipio_nascimento,
    p.uf_nascimento,
    p.foto_url,
    p.rede_social_url,
    p.site_url,
    p.escolaridade,
    p.situacao_atual,
    p.condicao_eleitoral,
    p.email_institucional,
    p.telefone_institucional,
    p.gabinete_endereco,
    p.pagina_url,
    pr.profissoes,
    p.id_captura,
    cast(p.dt_captura as date) as dt_captura

from uma_por_pessoa as p

left join {{ ref('int_pessoas_profissoes_agregadas') }} as pr on pr.id_pessoa = p.id_pessoa
