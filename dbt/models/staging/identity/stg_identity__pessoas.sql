with source as (

    select * from {{ source('identity', 'pessoa') }}

),

renamed as (

    select
        id_pessoa,
        try_cast(created_at as timestamp) as dt_criacao

    from source

)

select * from renamed
