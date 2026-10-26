-- A mesma pessoa em eleições diferentes do TSE (ADR 0025): mesmo nome civil e mesma data de nascimento, e a combinação
-- única em cada eleição. Se duas candidaturas da mesma eleição têm a combinação, nenhuma das duas liga (homônimo).
-- Datas de 1º de janeiro ficam de fora: o TSE usa o dia 1º de janeiro quando só conhece o ano, e isso juntaria pessoas
-- diferentes. O identificador não cria pessoa em `identity`: só diz quais candidaturas são da mesma pessoa.
with candidaturas as (

    select distinct
        id_candidatura,
        ano_eleicao,
        name_key(nome) as nome_chave,
        dt_nascimento

    from {{ ref('stg_tse__candidaturas') }}

    where name_key(nome) is not null
        and dt_nascimento is not null
        and dt_nascimento >= date '1900-01-01'
        and not (month(dt_nascimento) = 1 and day(dt_nascimento) = 1)

),

ambiguas as (

    select distinct nome_chave, dt_nascimento

    from candidaturas

    group by nome_chave, dt_nascimento, ano_eleicao

    having count(*) > 1

)

select
    c.id_candidatura,
    substr(md5(c.nome_chave || '|' || cast(c.dt_nascimento as varchar)), 1, 16) as id_pessoa_tse

from candidaturas as c

left join ambiguas as a on a.nome_chave = c.nome_chave and a.dt_nascimento = c.dt_nascimento

where a.nome_chave is null
