-- ADR 0057: o mesmo nome, casa e UF num dispositivo liga a uma só pessoa; qualquer linha aqui é vínculo que a regra não permite.
select id_dispositivo, casa, nome_parlamentar, uf
from {{ ref('fct_vetos_votos') }}
where id_pessoa is not null
group by id_dispositivo, casa, nome_parlamentar, uf
having count(distinct id_pessoa) > 1
