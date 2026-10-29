{{ config(severity='warn') }}
-- Municípios do TSE que não ligaram a um município do IBGE por nome e UF (grafia diferente entre as fontes, nome
-- repetido na mesma UF ou município que mudou de nome). Ficam sem código do IBGE; nada é inferido.
select
    cd_municipio_tse,
    nome_tse,
    uf

from {{ ref('dim_municipios_codigos_tse') }}

where id_municipio is null
