{{ config(severity='warn') }}
-- Mandatos cujo fim vem antes do início, como a fonte publica (por exemplo, registro de fim de mandato anterior à
-- posse na mesma legislatura). Não corrigimos a data: o caso fica medido aqui.
select
    id_pessoa,
    id_legislatura,
    dt_inicio,
    dt_fim

from {{ ref('mandatos') }}

where dt_fim < dt_inicio
