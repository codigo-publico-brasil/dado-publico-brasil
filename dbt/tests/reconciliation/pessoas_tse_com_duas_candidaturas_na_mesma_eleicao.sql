-- Erro se uma pessoa do TSE (int_tse_pessoas) tiver duas candidaturas na mesma eleição: seria a junção de pessoas diferentes.
select p.id_pessoa_tse, c.ano_eleicao

from {{ ref('int_tse_pessoas') }} as p

inner join {{ ref('stg_tse__candidaturas') }} as c on c.id_candidatura = p.id_candidatura

group by p.id_pessoa_tse, c.ano_eleicao

having count(distinct c.id_candidatura) > 1
