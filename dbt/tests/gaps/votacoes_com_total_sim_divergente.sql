{{ config(severity='warn') }}
-- Reconciliação com o total oficial: votações com votos individuais cujo total de Sim difere da contagem.
select v.votacao_id
from {{ ref('votacoes') }} as v
where v.votos_sim is not null
  and exists (select 1 from {{ ref('votos') }} as x where x.votacao_id = v.votacao_id)
  and v.votos_sim <> (
      select count(*) from {{ ref('votos') }} as x where x.votacao_id = v.votacao_id and x.voto = 'Sim'
  )
