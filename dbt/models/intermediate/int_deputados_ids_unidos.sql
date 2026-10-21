-- Todo deputado que a Câmara informa: o cadastro mais quem só aparece nos votos.
-- O código de identidade lê este modelo para dar a cada um a chave própria de pessoa.
select deputado_id from {{ ref('stg_camara__deputados') }}

union

select deputado_id from {{ ref('int_deputados_nos_votos_agregados') }}
