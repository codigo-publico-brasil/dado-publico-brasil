with source as (

    select * from {{ source('camara', 'proposicoes_tramitacoes') }}

),

renamed as (

    select
        try_cast(_item as bigint) as proposicao_id,
        try_cast(sequencia as integer) as sequencia,
        try_cast(data_hora as timestamp) as registrada_em,
        sigla_orgao as orgao_sigla,
        regime,
        descricao_tramitacao as descricao,
        try_cast(cod_tipo_tramitacao as integer) as tipo_id,
        sentence_case(descricao_situacao) as situacao,
        try_cast(cod_situacao as integer) as situacao_id,
        despacho,
        ambito,
        apreciacao,
        _source_file_id as source_file_id

    from source

)

select * from renamed
