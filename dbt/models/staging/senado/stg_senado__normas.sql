-- Catálogo das normas federais: uma linha por norma. Só metadados (o texto não vem desta API).
with source as (

    select * from {{ source('senado', 'normas') }}

)

select
    try_cast(id as bigint) as norma_id,
    tipo as tipo_sigla,
    descricao as tipo,
    numero,
    norma as identificador,
    norma_nome as nome,
    sentence_case(ementa) as ementa,
    ementa as ementa_oficial,
    try_strptime(dataassinatura, '%d/%m/%Y')::date as assinada_em,
    try_cast(anoassinatura as integer) as ano,
    -- "LEI-14116-2020-12-31 , Lei de Diretrizes Orçamentárias - LDO (2021)": o apelido é o que vem depois da vírgula
    nullif(trim(regexp_extract(apelido, ' , (.*)$', 1)), '') as apelido,
    _source_file_id as source_file_id

from source

qualify row_number() over (partition by id order by _source_file_id desc) = 1
