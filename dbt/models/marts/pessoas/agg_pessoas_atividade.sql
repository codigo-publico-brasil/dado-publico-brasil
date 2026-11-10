-- O que cada parlamentar fez (votos, propostas, legislaturas, último partido): muda a cada carga, por isso fica fora do
-- cadastro. Uma linha por pessoa de dim_pessoas_cadastro (Câmara e Senado); quem não votou fica com zero votos.
with votos as (

    select
        id_pessoa,
        count(*) as qtd_votos,
        arg_max(partido_sigla, dt_voto) as ultimo_partido,
        arg_max(uf_sigla, dt_voto) as ultima_uf,
        max(dt_voto) as dt_ultimo_voto,
        min(id_legislatura) as primeira_legislatura_com_voto,
        max(id_legislatura) as ultima_legislatura_com_voto

    from {{ ref('int_votacoes_votos_ligados') }}

    group by id_pessoa

),

propostas as (

    select id_pessoa, count(*) as qtd_propostas

    from {{ ref('int_proposicoes_autorias_ligadas') }}

    where id_pessoa is not null

    group by id_pessoa

)

select
    c.id_pessoa,
    coalesce(v.qtd_votos, 0) as qtd_votos,
    -- autoria só existe para a Câmara: nas demais fontes é desconhecida (vazio), não zero
    if(c.fonte = '{{ var("source_camara") }}', coalesce(p.qtd_propostas, 0), null) as qtd_propostas,
    v.ultimo_partido,
    v.ultima_uf,
    v.dt_ultimo_voto,
    v.primeira_legislatura_com_voto,
    v.ultima_legislatura_com_voto

from {{ ref('dim_pessoas_cadastro') }} as c

left join votos as v on v.id_pessoa = c.id_pessoa

left join propostas as p on p.id_pessoa = c.id_pessoa
