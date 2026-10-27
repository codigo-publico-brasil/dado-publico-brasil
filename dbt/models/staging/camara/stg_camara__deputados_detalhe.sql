with source as (

    select * from {{ source('camara', 'deputados_detalhe') }}

),

renamed as (

    select
        try_cast(regexp_extract(_item, '(\d+)$', 1) as bigint) as id_deputado,
        sentence_case(escolaridade) as escolaridade,
        ultimo_status_situacao as situacao,
        ultimo_status_condicao_eleitoral as condicao_eleitoral,
        nullif(trim(ultimo_status_gabinete_email), '') as gabinete_email,
        nullif(trim(ultimo_status_gabinete_telefone), '') as gabinete_telefone,
        nullif(
            concat_ws(', ',
                'prédio ' || nullif(trim(ultimo_status_gabinete_predio), ''),
                'sala ' || nullif(trim(ultimo_status_gabinete_sala), ''),
                'andar ' || nullif(trim(ultimo_status_gabinete_andar), '')),
            '') as gabinete_endereco,
        _source_file_id as id_captura

    from source

)

select * from renamed
