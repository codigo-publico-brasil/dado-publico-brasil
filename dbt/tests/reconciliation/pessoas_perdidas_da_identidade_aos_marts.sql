select 1
where (select count(*) from {{ ref('stg_identity__pessoas') }}) <> (select count(*) from {{ ref('pessoas') }})
