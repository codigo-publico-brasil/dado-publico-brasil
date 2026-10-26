-- Vínculos entre fontes, pela regra conservadora de ADR 0013: nome civil e data de nascimento iguais e únicos.
-- Segunda chave (ADR 0026), só para a candidatura que a primeira não ligou: nome de urna igual ao nome parlamentar e
-- mesma data de nascimento, também únicos (pega quem mudou de nome civil, como Erika Santos Silva, hoje Erika Hilton).
--  - "Único" quer dizer: dentro de cada fonte, só um registro tem aquele nome e nascimento (homônimo com a
--    mesma data não liga) e, numa eleição, só uma candidatura tem aquele nome e nascimento.
--  - Câmara e Senado ligados entre si dão a mesma pessoa (a identidade funde as duas chaves).
--  - A candidatura do TSE liga-se à pessoa (a âncora é o registro da Câmara, ou do Senado se não houver).
-- Quem não passa na regra não é ligado; os testes `pessoas_ambiguas_entre_fontes` e `eleitos_federais_sem_vinculo` medem isso.
--  - Os casos que a regra não resolve (homônimo, nome diferente entre as fontes) entram por `vinculos_aprovados`,
--    conferidos por uma pessoa, com a evidência escrita.
with pessoas as (

    select *

    from {{ ref('int_pessoas_vinculo') }}

    where nome_chave is not null and dt_nascimento is not null

),

chaves as (

    select
        nome_chave,
        dt_nascimento,
        max(id_na_fonte) filter (where fonte = '{{ var("source_camara") }}') as id_camara,
        max(id_na_fonte) filter (where fonte = '{{ var("source_senado") }}') as id_senado

    from pessoas

    group by nome_chave, dt_nascimento

    having count(*) filter (where fonte = '{{ var("source_camara") }}') <= 1
       and count(*) filter (where fonte = '{{ var("source_senado") }}') <= 1

),

chaves_urna as (

    select
        nome_urna_chave as nome_chave,
        dt_nascimento,
        max(id_na_fonte) filter (where fonte = '{{ var("source_camara") }}') as id_camara,
        max(id_na_fonte) filter (where fonte = '{{ var("source_senado") }}') as id_senado

    from {{ ref('int_pessoas_vinculo') }}

    where nome_urna_chave is not null and dt_nascimento is not null
        and not (month(dt_nascimento) = 1 and day(dt_nascimento) = 1)

    group by nome_urna_chave, dt_nascimento

    having count(*) filter (where fonte = '{{ var("source_camara") }}') <= 1
       and count(*) filter (where fonte = '{{ var("source_senado") }}') <= 1

),

candidaturas_urna as (

    select
        ano_eleicao,
        id_candidatura,
        name_key(nome_urna) as nome_chave,
        dt_nascimento

    from {{ ref('stg_tse__candidaturas') }}

    where nome_urna is not null and dt_nascimento is not null

    qualify count(distinct id_candidatura) over (partition by ano_eleicao, name_key(nome_urna), dt_nascimento) = 1

),

candidaturas as (
    select
        ano_eleicao,
        id_candidatura,
        name_key(nome) as nome_chave,
        dt_nascimento

    from {{ ref('stg_tse__candidaturas') }}

    where nome is not null and dt_nascimento is not null

    qualify count(distinct id_candidatura) over (partition by ano_eleicao, name_key(nome), dt_nascimento) = 1

),

candidaturas_ligadas_pelo_nome_civil as (

    select c.id_candidatura

    from candidaturas as c

    inner join chaves as k on k.nome_chave = c.nome_chave and k.dt_nascimento = c.dt_nascimento

)

select
    '{{ var("source_camara") }}' as origem_fonte,
    '{{ var("id_type_camara") }}' as origem_tipo,
    id_camara as id_origem,
    '{{ var("source_senado") }}' as destino_fonte,
    '{{ var("id_type_senado") }}' as destino_tipo,
    id_senado as id_destino,
    'nome civil e data de nascimento iguais e únicos' as metodo

from chaves

where id_camara is not null and id_senado is not null

union all

select distinct
    '{{ var("source_tse") }}',
    '{{ var("id_type_tse") }}',
    c.id_candidatura,
    if(k.id_camara is not null, '{{ var("source_camara") }}', '{{ var("source_senado") }}'),
    if(k.id_camara is not null, '{{ var("id_type_camara") }}', '{{ var("id_type_senado") }}'),
    coalesce(k.id_camara, k.id_senado),
    'nome civil e data de nascimento iguais e únicos'

from candidaturas as c

inner join chaves as k on k.nome_chave = c.nome_chave and k.dt_nascimento = c.dt_nascimento

union all

select distinct
    '{{ var("source_tse") }}',
    '{{ var("id_type_tse") }}',
    c.id_candidatura,
    if(k.id_camara is not null, '{{ var("source_camara") }}', '{{ var("source_senado") }}'),
    if(k.id_camara is not null, '{{ var("id_type_camara") }}', '{{ var("id_type_senado") }}'),
    coalesce(k.id_camara, k.id_senado),
    'nome de urna e data de nascimento iguais e únicos'

from candidaturas_urna as c

inner join chaves_urna as k on k.nome_chave = c.nome_chave and k.dt_nascimento = c.dt_nascimento

where c.id_candidatura not in (select id_candidatura from candidaturas_ligadas_pelo_nome_civil)

union all

select
    origem_fonte,
    origem_tipo,
    id_origem,
    destino_fonte,
    destino_tipo,
    id_destino,
    'vínculo aprovado por ' || aprovado_por || ' em ' || dt_aprovacao

from {{ ref('vinculos_aprovados') }}
