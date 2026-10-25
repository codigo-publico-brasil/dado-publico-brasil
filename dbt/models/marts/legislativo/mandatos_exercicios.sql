-- Exercício oficial no cargo, como o Senado informa: titulares e suplentes, com início, fim e causa de
-- afastamento. Só quem assumiu aparece (suplente que nunca assumiu não tem exercício). A Câmara não publica
-- este dado, então a tabela só tem o Senado.
select
    '{{ var("source_senado") }}' as fonte,
    i.id_pessoa,
    e.id_mandato,
    e.id_exercicio,
    e.participacao,
    e.uf,
    e.dt_mandato_inicio,
    e.dt_mandato_fim,
    e.dt_inicio,
    e.dt_fim,
    e.causa_afastamento_sigla,
    e.causa_afastamento

from {{ ref('stg_senado__exercicios') }} as e

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_senado") }}'
    and i.id_tipo = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(e.id_senador as varchar)
