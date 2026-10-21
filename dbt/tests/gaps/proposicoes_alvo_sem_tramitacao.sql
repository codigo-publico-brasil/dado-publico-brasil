{{ config(severity='warn') }}
-- Proposições que podem virar norma e ainda não tiveram a tramitação buscada (a carga é por amostra, dos
-- itens mais recentes para os mais antigos): mede quanto falta.
select p.proposicao_id
from {{ ref('proposicoes') }} as p
where p.fonte = '{{ var("source_camara") }}'
  and split_part(p.sigla, ' ', 1) in ('PL', 'PLP', 'PEC', 'MPV', 'PDL', 'PLV', 'PLN', 'PRC')
  and not exists (
      select 1 from {{ ref('tramitacoes') }} as t where t.fonte = p.fonte and t.proposicao_id = p.proposicao_id
  )
