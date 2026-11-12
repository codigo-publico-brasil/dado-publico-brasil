-- Topo do Executivo federal (PEP): uma linha por pessoa, função, órgão e início de exercício, em cada mês capturado.
-- "Não informada" vira vazio (a data não existe na fonte; nada é estimado).
with base as (

select
    proper_name(nome_pep) as nome,
    sigla_fun_o as cd_funcao,
    descri_o_fun_o as funcao,
    n_vel_fun_o as cd_nivel_funcao,
    nome_rg_o as orgao,
    try_strptime(data_in_cio_exerc_cio, '%d/%m/%Y')::date as dt_inicio,
    try_strptime(data_fim_exerc_cio, '%d/%m/%Y')::date as dt_fim,
    try_strptime(data_fim_car_ncia, '%d/%m/%Y')::date as dt_fim_carencia,
    _source_file_id as id_captura

from {{ source('pep', 'dirigentes') }}

)

{{ colunas_auditoria('base') }}
