-- Pessoa sem nenhum identificador de fonte não tem origem rastreável.
select p.id_pessoa
from {{ ref('stg_identity__pessoas') }} as p
where not exists (
    select 1 from {{ ref('stg_identity__pessoa_identificadores') }} as i where i.id_pessoa = p.id_pessoa
)
