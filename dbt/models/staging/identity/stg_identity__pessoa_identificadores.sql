with source as (

    select * from {{ source('identity', 'pessoa_identificador') }}

),

renamed as (

    select
        id_pessoa,
        source as fonte,
        id_type as tipo_id,
        source_id as id_na_fonte,
        method as metodo,
        confirmed_by as confirmado_por,
        try_cast(linked_at as timestamp) as ligada_em

    from source

)

select * from renamed
