{{ config(severity='warn') }}
-- Lacuna conhecida da fonte: muitas proposições vêm sem a última situação.
select id_proposicao from {{ ref('proposicoes') }}
where fonte = '{{ var("source_camara") }}' and situacao is null
