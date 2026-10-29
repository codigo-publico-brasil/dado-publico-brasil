{{ config(severity='warn') }}
-- Reconciliação com o total oficial: votações com votos individuais cujo total de Sim difere da contagem.
-- Votação secreta fica de fora: a fonte não informa a escolha, então não há Sim para contar.
select v.id_votacao
from {{ ref('fct_votacoes') }} as v
where v.votos_sim is not null
  and not coalesce(v.fl_votacao_secreta, false)
  and exists (select 1 from {{ ref('fct_votos') }} as x where x.fonte = v.fonte and x.id_votacao = v.id_votacao)
  and v.votos_sim <> (
      select count(*) from {{ ref('fct_votos') }} as x
      where x.fonte = v.fonte and x.id_votacao = v.id_votacao and x.voto = 'Sim'
  )
