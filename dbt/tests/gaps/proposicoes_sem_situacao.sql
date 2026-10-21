{{ config(severity='warn') }}
-- Lacuna conhecida da fonte: muitas proposições vêm sem a última situação.
select proposicao_id from {{ ref('proposicoes') }} where situacao is null
