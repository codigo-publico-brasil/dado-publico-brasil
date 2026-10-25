-- Todo deputado que a Câmara informa: o cadastro mais quem só aparece nos votos.
-- O código de identidade lê este modelo para dar a cada um a chave própria de pessoa.
select id_deputado from {{ ref('stg_camara__deputados') }}

union

select id_deputado from {{ ref('int_deputados_votos_agregados') }}
