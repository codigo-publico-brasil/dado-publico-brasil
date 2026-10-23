{{ config(severity='warn') }}
-- Nome civil e nascimento que se repetem dentro da mesma fonte: a regra não liga (homônimo), e a curadoria decide.
select nome_chave, nascimento, fonte, count(*) as registros
from {{ ref('int_pessoas_para_vinculo') }}
where nome_chave is not null and nascimento is not null
group by nome_chave, nascimento, fonte
having count(*) > 1
