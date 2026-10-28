{{ config(severity='warn') }}
-- Pessoa de core.pessoas sem nenhum partido conhecido (nem no histórico da Câmara nem em candidatura do TSE com partido
-- curado). Hoje esperado: pessoa só com registros "sem partido" ou com sigla ainda não curada.
select p.id_pessoa
from {{ ref('core_pessoas') }} as p
where not exists (
    select 1 from {{ ref('fatos_pessoas_partidos') }} as f where f.id_pessoa = p.id_pessoa and f.id_partido is not null
)
