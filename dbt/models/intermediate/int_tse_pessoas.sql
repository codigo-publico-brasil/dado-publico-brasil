-- A mesma pessoa em eleições diferentes do TSE (ADRs 0025 e 0026). Duas chaves, cada uma com a data de nascimento:
--  - o nome civil: a regra de base;
--  - o nome de urna, na mesma UF: pega quem mudou de nome civil entre as eleições (uma pessoa que trocou de nome civil entre as eleições).
-- Cada chave só vale quando é única em cada eleição (duas candidaturas da mesma eleição com a chave: homônimo, nenhuma liga)
-- e sem datas de 1º de janeiro (o TSE usa o dia 1º de janeiro quando só conhece o ano, e isso juntaria pessoas diferentes).
-- Candidaturas que partilham uma das chaves são da mesma pessoa, e a ligação se propaga: A liga com B por uma chave e B
-- com C pela outra, então A, B e C são a mesma. Uma pessoa não tem duas candidaturas na mesma eleição: o grupo em que isso
-- acontece juntou pessoas diferentes (homônimos com o mesmo nome de urna e nascimento) e é descartado inteiro.
-- O identificador não cria pessoa em `identity`.
with candidaturas as (

    select distinct
        id_candidatura,
        ano_eleicao,
        name_key(nome) || '|' || cast(dt_nascimento as varchar) as chave_civil,
        name_key(nome_urna) || '|' || cast(dt_nascimento as varchar) || '|' || uf as chave_urna

    from {{ ref('stg_tse__candidaturas') }}

    where dt_nascimento is not null
        and dt_nascimento >= date '1900-01-01'
        and not (month(dt_nascimento) = 1 and day(dt_nascimento) = 1)

),

ambiguas as (

    select chave_civil as chave from candidaturas group by chave_civil, ano_eleicao having count(*) > 1

    union

    select chave_urna from candidaturas group by chave_urna, ano_eleicao having count(*) > 1

),

validas as (

    select
        c.id_candidatura,
        c.ano_eleicao,
        if(a1.chave is null and c.chave_civil not like '|%', c.chave_civil, null) as chave_civil,
        if(a2.chave is null and c.chave_urna not like '|%', c.chave_urna, null) as chave_urna

    from candidaturas as c

    left join ambiguas as a1 on a1.chave = c.chave_civil

    left join ambiguas as a2 on a2.chave = c.chave_urna

),

-- rótulo inicial: a menor das duas chaves; depois, três rodadas em que cada candidatura adota o menor rótulo de quem
-- partilha uma das suas chaves (sem chave, a candidatura fica sozinha: o nulo não pode formar um grupo)
r0 as (

    select
        id_candidatura,
        ano_eleicao,
        chave_civil,
        chave_urna,
        least(coalesce(chave_civil, chave_urna), coalesce(chave_urna, chave_civil)) as rotulo

    from validas

    where chave_civil is not null or chave_urna is not null

),

r1 as (

    select
        id_candidatura,
        ano_eleicao,
        chave_civil,
        chave_urna,
        least(
            rotulo,
            coalesce(min(rotulo) over (partition by coalesce(chave_civil, id_candidatura)), rotulo),
            coalesce(min(rotulo) over (partition by coalesce(chave_urna, id_candidatura)), rotulo)
        ) as rotulo

    from r0

),

r2 as (

    select
        id_candidatura,
        ano_eleicao,
        chave_civil,
        chave_urna,
        least(
            rotulo,
            coalesce(min(rotulo) over (partition by coalesce(chave_civil, id_candidatura)), rotulo),
            coalesce(min(rotulo) over (partition by coalesce(chave_urna, id_candidatura)), rotulo)
        ) as rotulo

    from r1

),

r3 as (

    select
        id_candidatura,
        ano_eleicao,
        least(
            rotulo,
            coalesce(min(rotulo) over (partition by coalesce(chave_civil, id_candidatura)), rotulo),
            coalesce(min(rotulo) over (partition by coalesce(chave_urna, id_candidatura)), rotulo)
        ) as rotulo

    from r2

)

select
    id_candidatura,
    substr(md5(rotulo), 1, 16) as id_pessoa_tse

from r3

qualify count(*) over (partition by rotulo) = count(distinct ano_eleicao) over (partition by rotulo)
