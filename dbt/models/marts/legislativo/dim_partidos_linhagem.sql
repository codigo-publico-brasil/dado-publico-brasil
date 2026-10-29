-- O que mudou na vida de cada partido (mudança de nome, fusão, incorporação), conforme o TSE. Curada à mão
-- em dbt/seeds/eventos_de_partidos.csv, com a página oficial de cada evento; só entra o que foi conferido.
-- A sigla sozinha não identifica o partido (uma mesma sigla pode designar dois partidos em épocas diferentes): use a data.
select
    sigla_anterior,
    sigla_posterior,
    tipo,
    dt_aprovacao,
    ano,
    fonte_url,
    observacao

from {{ ref('partidos_eventos') }}
