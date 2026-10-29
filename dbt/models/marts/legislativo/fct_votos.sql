-- O voto nominal de cada parlamentar em cada votação (Câmara e Senado), com o partido que a pessoa tinha na data do voto
-- como chave (`id_partido`) e a sigla da fonte ao lado. Substitui o texto do partido de fct_votos.
-- A sigla pode ser de dois partidos (duas legendas diferentes em épocas diferentes): vale o partido cujo período de uso da sigla está
-- mais perto do ano do voto (partidos_siglas). Sem partido ("S.Part.", "Sem registro") ou sigla ainda não curada,
-- o id_partido fica vazio e o teste de aviso mede.
with siglas as (

    select id_partido, upper(replace(sigla_na_fonte, ' ', '')) as sigla_chave, ano_inicio, ano_fim

    from {{ ref('partidos_siglas') }}

),

combinacoes as (

    select distinct upper(replace(partido_sigla, ' ', '')) as sigla_chave, year(dt_voto) as ano

    from {{ ref('int_votacoes_votos_ligados') }}

    where partido_sigla is not null and dt_voto is not null

),

mapa as (

    -- uma conta por combinação de sigla e ano (poucas centenas), e não por voto (milhões)
    select
        c.sigla_chave,
        c.ano,
        (
            select s.id_partido
            from siglas as s
            where s.sigla_chave = c.sigla_chave
            order by greatest(s.ano_inicio - c.ano, c.ano - s.ano_fim, 0)
            limit 1
        ) as id_partido

    from combinacoes as c

)

select
    v.fonte,
    v.id_votacao,
    v.id_pessoa,
    v.voto,
    v.dt_voto,
    m.id_partido,
    v.partido_sigla as partido_na_fonte,
    v.uf_sigla as uf,
    v.id_captura

from {{ ref('int_votacoes_votos_ligados') }} as v

left join mapa as m on m.sigla_chave = upper(replace(v.partido_sigla, ' ', '')) and m.ano = year(v.dt_voto)
