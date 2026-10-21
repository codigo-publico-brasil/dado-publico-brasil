with source as (

    select * from {{ source('metadata', 'captures') }}

),

renamed as (

    select
        id as source_file_id,
        source as fonte,
        dataset,
        year as ano,
        url,
        sha256,
        try_cast(captured_at as timestamp) as capturado_em,
        try_cast(last_checked_at as timestamp) as verificado_em

    from source

)

select * from renamed
