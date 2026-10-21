select
    p.id_pessoa,
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
    coalesce(a.qtd_propostas, 0) as qtd_propostas,
    coalesce(a.qtd_votos, 0) as qtd_votos,
    (
        select cast(max(capturado_em) as date)
        from {{ ref('stg_metadata__captures') }}
        where dataset = 'deputados'
    ) as capturado_em

from {{ ref('int_pessoas_unidas_ao_cadastro') }} as p

left join {{ ref('int_pessoas_atividade_agregada') }} as a on a.id_pessoa = p.id_pessoa

left join {{ ref('int_pessoas_profissoes_agregadas') }} as pr on pr.id_pessoa = p.id_pessoa
