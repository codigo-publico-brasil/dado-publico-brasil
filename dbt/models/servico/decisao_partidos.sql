-- O voto por partido em cada votação, com a sigla do partido como estava no voto (marts.votacoes_votos ainda não traz o
-- id_partido; ele entra quando houver fatos.votos).
select
    fonte,
    id_votacao,
    partido as partido_no_voto,
    voto,
    count(*) as qtd_votos

from {{ ref('votacoes_votos') }}

group by fonte, id_votacao, partido, voto
