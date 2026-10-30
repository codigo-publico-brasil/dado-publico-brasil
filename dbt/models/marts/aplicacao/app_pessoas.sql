-- A ficha cadastral de cada pessoa do projeto (quem já foi eleito), com a foto. Só leitura do núcleo e dos marts.
-- Regra: todo atributo que alguma fonte oficial carregada tem, a ficha tem. O cadastro da Câmara e do Senado vale primeiro
-- (mais completo); o que ele não traz, ou quem nunca passou por ele, vem da candidatura mais recente do TSE que o informa.
-- Contato institucional, redes, site e falecimento só existem no cadastro das casas e ficam vazios para os demais.
-- `foto_caminho` é a foto oficial do TSE (arquivo local); `foto_url` é a da Câmara ou do Senado.
with tse as (

    -- de cada atributo, o valor da candidatura mais recente que o informa
    select
        ca.id_pessoa,
        arg_max(ca.foto_caminho, a.ano_eleicao) filter (where ca.foto_caminho is not null) as foto_caminho,
        arg_max(ca.uf_nascimento, a.ano_eleicao) filter (where ca.uf_nascimento is not null) as uf_nascimento,
        arg_max(ca.grau_instrucao, a.ano_eleicao) filter (where ca.grau_instrucao is not null) as grau_instrucao,
        arg_max(ca.ocupacao, a.ano_eleicao) filter (where ca.ocupacao is not null) as ocupacao,
        arg_max(ca.estado_civil, a.ano_eleicao) filter (where ca.estado_civil is not null) as estado_civil,
        arg_max(ca.nome_social, a.ano_eleicao) filter (where ca.nome_social is not null) as nome_social,
        arg_max(ca.id_captura, a.ano_eleicao) as id_captura

    from {{ ref('fct_candidaturas') }} as ca

    inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
        on a.id_candidatura = ca.id_candidatura

    where ca.id_pessoa is not null

    group by ca.id_pessoa

),

captura_cadastro as (

    -- a captura mais recente do cadastro de cada casa (deputados e senadores)
    select fonte, arg_max(url, dt_captura) as url, cast(max(dt_captura) as date) as dt_captura

    from {{ ref('stg_metadata__captures') }}

    where dataset in ('deputados', 'senadores')

    group by fonte

)

select
    p.id_pessoa,
    p.nome_publico as nome,
    p.nome_civil,
    t.nome_social,
    p.genero,
    p.dt_nascimento,
    c.dt_falecimento,
    c.municipio_nascimento,
    coalesce(c.uf_nascimento, t.uf_nascimento) as uf_nascimento,
    coalesce(c.escolaridade, t.grau_instrucao) as escolaridade,
    t.estado_civil,
    coalesce(c.profissoes, t.ocupacao) as profissoes,
    c.situacao_atual,
    c.email_institucional,
    c.telefone_institucional,
    c.gabinete_endereco,
    c.pagina_url,
    c.site_url,
    c.rede_social_url,
    t.foto_caminho,
    c.foto_url,
    c.fontes,
    coalesce(cc.url, ct.url) as fonte_url,
    coalesce(cc.dt_captura, cast(ct.dt_captura as date)) as dt_captura

from {{ ref('dim_pessoas') }} as p

left join {{ ref('dim_pessoas_cadastro') }} as c on c.id_pessoa = p.id_pessoa

left join tse as t on t.id_pessoa = p.id_pessoa

left join captura_cadastro as cc on cc.fonte = c.fonte

left join {{ ref('stg_metadata__captures') }} as ct on ct.id_captura = t.id_captura
