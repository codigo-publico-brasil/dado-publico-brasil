{{ config(severity='warn') }}
-- Votação simbólica não tem voto individual: a página deve dizer "sem voto individual".
select v.votacao_id
from {{ ref('votacoes') }} as v
where not exists (select 1 from {{ ref('votos') }} as x where x.votacao_id = v.votacao_id)
