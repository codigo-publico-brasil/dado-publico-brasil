-- A mesma pessoa aparece no arquivo de cada legislatura que ela atravessou: o staging fica com uma linha
-- por senador, com os dados do arquivo mais recente.
with source as (

    select * from {{ source('senado', 'senadores') }}

)

select
    try_cast(identificacao_parlamentar_codigo_parlamentar as bigint) as senador_id,
    arg_max(proper_name(identificacao_parlamentar_nome_parlamentar), _source_file_id) as nome,
    arg_max(proper_name(identificacao_parlamentar_nome_completo_parlamentar), _source_file_id) as nome_civil,
    arg_max(
        case identificacao_parlamentar_sexo_parlamentar when 'Masculino' then 'M' when 'Feminino' then 'F' end,
        _source_file_id
    ) as sexo,
    max(_source_file_id) as source_file_id

from source

group by 1
