-- As candidaturas do TSE de quem foi eleito pelo menos uma vez: a base das pessoas de todo eleito (ADR 0031). `grupo` é a
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
    c.id_candidatura,
    coalesce(p.id_pessoa_tse, c.id_candidatura) as grupo,
    c.fl_eleita

from candidaturas as c

left join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

qualify bool_or(c.fl_eleita) over (partition by coalesce(p.id_pessoa_tse, c.id_candidatura))
