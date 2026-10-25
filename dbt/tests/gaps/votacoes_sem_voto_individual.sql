{{ config(severity='warn') }}
-- Votação simbólica (ou sem registro) não tem voto individual: a página deve dizer "sem voto individual".
select v.id_votacao
from {{ ref('votacoes') }} as v
where not exists (
    select 1 from {{ ref('votacoes_votos') }} as x where x.fonte = v.fonte and x.id_votacao = v.id_votacao
)
