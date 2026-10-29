{{ config(severity='warn') }}
-- Normas que a fonte lista sem a sigla do tipo (12 em 23/10/2026). Ficam no catálogo com o tipo vazio, nada é inferido.
select id_norma from {{ ref('fct_normas') }} where tipo_sigla is null
