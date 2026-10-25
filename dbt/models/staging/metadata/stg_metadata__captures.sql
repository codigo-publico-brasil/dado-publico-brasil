with source as (

    select * from {{ source('metadata', 'captures') }}

),

renamed as (

    select
        id as id_captura,
        source as fonte,
        dataset,
        year as ano,
        url,
        sha256,
        try_cast(captured_at as timestamp) as dt_captura,
        try_cast(last_checked_at as timestamp) as dt_verificacao

    from source

)

select * from renamed
