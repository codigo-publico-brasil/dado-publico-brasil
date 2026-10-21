with cadastro as (

    select
        id_pessoa, fonte, nome, nome_civil, sexo, data_nascimento, data_falecimento, municipio_nascimento,
        uf_nascimento, foto_url, rede_social_url, site_url
    from {{ ref('int_pessoas_unidas_ao_cadastro') }}

    union all

    select
        id_pessoa, fonte, nome, nome_civil, sexo, data_nascimento, data_falecimento, municipio_nascimento,
        uf_nascimento, foto_url, rede_social_url, site_url
    from {{ ref('int_pessoas_do_senado_unidas_ao_cadastro') }}

),

capturas as (

    select fonte, cast(max(capturado_em) as date) as capturado_em

    from {{ ref('stg_metadata__captures') }}

    where dataset in ('deputados', 'senadores')

    group by fonte

)

select
    p.id_pessoa,
    p.fonte,
    p.nome,
    p.nome_civil,
    lower(strip_accents(p.nome)) as nome_ordem,
    lower(strip_accents(p.nome || ' ' || coalesce(p.nome_civil, ''))) as nome_busca,
    p.sexo,
    p.data_nascimento,
    p.data_falecimento,
    p.municipio_nascimento,
    p.uf_nascimento,
    p.foto_url,
    p.rede_social_url,
    p.site_url,
    a.primeira_legislatura_com_voto,
    a.ultima_legislatura_com_voto,
    pr.profissoes,
    a.ultimo_partido,
    a.ultima_uf,
    a.ultimo_voto_em,
    -- autoria só existe para a Câmara: nas demais fontes é desconhecida (vazio), não zero
    if(p.fonte = '{{ var("source_camara") }}', coalesce(a.qtd_propostas, 0), null) as qtd_propostas,
    coalesce(a.qtd_votos, 0) as qtd_votos,
    c.capturado_em

from cadastro as p

left join {{ ref('int_pessoas_atividade_agregada') }} as a on a.id_pessoa = p.id_pessoa

left join {{ ref('int_pessoas_profissoes_agregadas') }} as pr on pr.id_pessoa = p.id_pessoa

left join capturas as c on c.fonte = p.fonte
