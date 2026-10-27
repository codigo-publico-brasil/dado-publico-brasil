{{ config(severity='warn') }}
-- Candidaturas ao Congresso que a fonte marca como eleitas e a regra (nome civil e nascimento únicos) não ligou a uma
-- pessoa: homônimo, nome diferente entre as fontes ou nascimento ausente.
select c.id_candidatura
from {{ ref('stg_tse__candidaturas') }} as c
where c.resultado like 'Eleito%'
  and c.cargo in ('Deputado federal', 'Senador')
  and not exists (
      select 1 from {{ ref('stg_identity__pessoa_identificadores') }} as i
      where i.fonte = '{{ var("source_tse") }}' and i.id_tipo = '{{ var("id_type_tse") }}' and i.id_na_fonte = c.id_candidatura
  )
