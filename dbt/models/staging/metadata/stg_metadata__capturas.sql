with source as (

    select * from {{ source('metadata', 'capturas') }}

),

renamed as (

    select
        id_captura,
        fonte,
        dataset,
        particao,
        url,
        sha256,
        dt_captura,
        dt_verificacao

    from source

)

select * from renamed
