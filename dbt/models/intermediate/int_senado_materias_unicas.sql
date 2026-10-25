-- Re-granularidade: de uma linha por votação para uma por matéria (a mais recente votada).
select
    id_materia,
    arg_max(materia_sigla, dt_votacao) as sigla,
    arg_max(materia_ementa, dt_votacao) as ementa,
    arg_max(dt_materia_apresentacao, dt_votacao) as dt_apresentacao,
    arg_max(id_captura, dt_votacao) as id_captura

from {{ ref('stg_senado__votacoes') }}

where id_materia is not null

group by id_materia
