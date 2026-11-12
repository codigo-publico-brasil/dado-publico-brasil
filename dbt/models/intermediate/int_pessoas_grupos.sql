-- Grupos de registros que são uma pessoa só, lidos pela identidade sem saber de que fonte vêm (ADR 0053). Hoje há um
-- produtor: as candidaturas do TSE de quem foi eleito pelo menos uma vez: a base das pessoas de todo eleito (ADR 0031). `grupo` é a
-- pessoa entre as eleições (`id_pessoa_tse`); sem ele (nenhum nome e nascimento únicos) a candidatura é o próprio grupo.
-- O grupo NÃO é estável (muda se entra uma candidatura com outro nome): a identidade ancora em `id_candidatura`, que é.
-- Entram todas as candidaturas do grupo, não só a eleita, para o histórico ficar na mesma pessoa. Quem só se candidatou
-- e nunca foi eleito não aparece.
with candidaturas as (

    select distinct c.id_candidatura, e.id_candidatura is not null as fl_eleita

    from {{ ref('stg_tse__candidaturas') }} as c

    left join {{ ref('int_tse_eleitos') }} as e on e.id_candidatura = c.id_candidatura

)

select
    '{{ var("source_tse") }}' as fonte,
    '{{ var("id_type_tse_eleito") }}' as id_tipo,
    c.id_candidatura as id_na_fonte,
    coalesce(p.id_pessoa_tse, c.id_candidatura) as grupo,
    'candidaturas do mesmo grupo de eleito no TSE' as metodo,
    'mesmo grupo de candidaturas do TSE' as metodo_fusao

from candidaturas as c

left join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

qualify bool_or(c.fl_eleita) over (partition by coalesce(p.id_pessoa_tse, c.id_candidatura))
