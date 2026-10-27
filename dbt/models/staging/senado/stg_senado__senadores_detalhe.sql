with source as (

    select * from {{ source('senado', 'senadores_detalhe') }}

)

select
    try_cast(_item as bigint) as id_senador,
    proper_name(identificacao_parlamentar_nome_completo_parlamentar) as nome_civil,
    try_cast(dados_basicos_parlamentar_data_nascimento as date) as dt_nascimento,
    dados_basicos_parlamentar_naturalidade as municipio_nascimento,
    dados_basicos_parlamentar_uf_naturalidade as uf_nascimento,
    identificacao_parlamentar_url_foto_parlamentar as foto_url,
    identificacao_parlamentar_url_pagina_parlamentar as pagina_url,
    identificacao_parlamentar_url_pagina_particular as pagina_particular_url,
    nullif(trim(identificacao_parlamentar_email_parlamentar), '') as gabinete_email,
    nullif(trim(dados_basicos_parlamentar_endereco_parlamentar), '') as gabinete_endereco,
    (
        select string_agg(t.numero_telefone, '; ' order by t.ordem_publicacao)
        from {{ source('senado', 'senadores_detalhe__telefones_telefone') }} as t
        where t._dlt_parent_id = source._dlt_id
    ) as gabinete_telefone,
    _source_file_id as id_captura

from source
