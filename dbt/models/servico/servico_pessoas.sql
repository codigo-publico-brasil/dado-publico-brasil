{{ config(alias='pessoas') }}
-- A ficha cadastral de cada pessoa do projeto (quem já foi eleito), com a foto. Só leitura do núcleo e dos marts: o cadastro
-- de contato, escolaridade e profissões só existe para quem passou pela Câmara ou pelo Senado, e fica vazio para os demais.
-- `foto_caminho` é a foto oficial do TSE da candidatura mais recente (arquivo local); `foto_url` é a da Câmara ou do Senado.
with foto_tse as (

    select ca.id_pessoa, ca.foto_caminho

    from {{ ref('fatos_candidaturas') }} as ca

    inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
        on a.id_candidatura = ca.id_candidatura

    where ca.id_pessoa is not null and ca.foto_caminho is not null

    qualify row_number() over (partition by ca.id_pessoa order by a.ano_eleicao desc) = 1

)

select
    p.id_pessoa,
    p.nome_publico as nome,
    p.nome_civil,
    p.genero,
    p.dt_nascimento,
    c.dt_falecimento,
    c.municipio_nascimento,
    c.uf_nascimento,
    c.escolaridade,
    c.profissoes,
    c.situacao_atual,
    c.email_institucional,
    c.telefone_institucional,
    c.gabinete_endereco,
    c.pagina_url,
    c.site_url,
    c.rede_social_url,
    f.foto_caminho,
    c.foto_url,
    c.fontes,
    c.dt_captura

from {{ ref('core_pessoas') }} as p

left join {{ ref('pessoas') }} as c on c.id_pessoa = p.id_pessoa

left join foto_tse as f on f.id_pessoa = p.id_pessoa
