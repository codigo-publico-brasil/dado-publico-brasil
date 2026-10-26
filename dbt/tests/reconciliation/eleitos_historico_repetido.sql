-- Erro se um eleito tiver duas linhas de histórico para a mesma eleição e o mesmo cargo.
select id_candidatura, ano_eleicao, cargo

from {{ ref('eleitos_historico') }}

group by id_candidatura, ano_eleicao, cargo

having count(*) > 1
