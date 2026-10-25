with source as (

    select * from {{ source('identity', 'pessoa_identificador') }}

),

renamed as (

    select
        id_pessoa,
        source as fonte,
        id_type as id_tipo,
        source_id as id_na_fonte,
        method as metodo,
        confirmed_by as confirmado_por,
        try_cast(linked_at as timestamp) as dt_ligacao

    from source

)

select * from renamed
