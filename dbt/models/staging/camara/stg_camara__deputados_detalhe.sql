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
        ultimo_status_nome_eleitoral as nome_eleitoral,
        ultimo_status_sigla_partido as partido_sigla,
        ultimo_status_sigla_uf as uf_sigla,
        try_cast(ultimo_status_id_legislatura as integer) as id_legislatura,
        try_cast(ultimo_status_data as date) as dt_status,
        nullif(trim(ultimo_status_gabinete_nome), '') as gabinete_nome,
        _source_file_id as id_captura

    from source

)

{{ colunas_auditoria('renamed') }}
