with source as (

    select * from {{ source('senado', 'senadores_detalhe') }}

)

select
    try_cast(_item as bigint) as senador_id,
    proper_name(identificacao_parlamentar_nome_completo_parlamentar) as nome_civil,
    try_cast(dados_basicos_parlamentar_data_nascimento as date) as nascimento,
    dados_basicos_parlamentar_naturalidade as municipio_nascimento,
    dados_basicos_parlamentar_uf_naturalidade as uf_nascimento,
    identificacao_parlamentar_url_foto_parlamentar as foto_url,
    _source_file_id as source_file_id

from source
