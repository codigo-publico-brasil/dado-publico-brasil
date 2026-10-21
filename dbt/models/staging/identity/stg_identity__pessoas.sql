with source as (

    select * from {{ source('identity', 'pessoa') }}

),

renamed as (

    select
        id_pessoa,
        try_cast(created_at as timestamp) as criada_em

    from source

)

select * from renamed
