with source as (

    select * from {{ source('ibge', 'municipios') }}

)

select
    try_cast(id as integer) as id_municipio,
    nome,
    regiao_imediata_nome as regiao_imediata,
    regiao_imediata_regiao_intermediaria_nome as regiao_intermediaria,
    regiao_imediata_regiao_intermediaria_uf_sigla as uf,
    regiao_imediata_regiao_intermediaria_uf_nome as uf_nome,
    regiao_imediata_regiao_intermediaria_uf_regiao_sigla as regiao_sigla,
    regiao_imediata_regiao_intermediaria_uf_regiao_nome as regiao_nome,
    _source_file_id as id_captura

from source
