{{ config(severity='warn') }}
-- Mandatos de senador sem início do exercício oficial. O Senado publica o exercício de todo titular e suplente
-- que assumiu; sobra aqui quem tem voto registrado mas nenhum exercício que toque a legislatura.
select
    id_pessoa,
    id_legislatura

from {{ ref('mandatos') }}

where fonte = '{{ var("source_senado") }}'
    and dt_inicio is null
