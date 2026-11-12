-- Medição no nível do tempo: quando cada dataset de cada fonte trouxe conteúdo novo e quando foi consultado pela
-- última vez. Só mínimo, máximo e contagem das capturas; o atraso, que exige uma expectativa com fonte, não entra.
select
    fonte,
    dataset,
    count(*) as qtd_capturas,
    count(distinct particao) as qtd_particoes,
    min(dt_captura) as dt_primeira_captura,
    max(dt_captura) as dt_ultima_captura,
    max(dt_verificacao) as dt_ultima_verificacao

from {{ ref('stg_metadata__capturas') }}

group by fonte, dataset
