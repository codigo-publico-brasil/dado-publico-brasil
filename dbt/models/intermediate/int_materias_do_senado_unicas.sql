-- Re-granularidade: de uma linha por votação para uma por matéria (a mais recente votada).
select
    materia_id,
    arg_max(materia_sigla, data) as sigla,
    arg_max(materia_ementa, data) as ementa,
    arg_max(materia_apresentada_em, data) as apresentada_em,
    arg_max(source_file_id, data) as source_file_id

from {{ ref('stg_senado__votacoes') }}

where materia_id is not null

group by materia_id
