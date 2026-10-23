-- Vínculos entre fontes, pela regra conservadora de ADR 0013: nome civil e data de nascimento iguais e únicos.
--  - "Único" quer dizer: dentro de cada fonte, só um registro tem aquele nome e nascimento (homônimo com a
--    mesma data não liga) e, numa eleição, só uma candidatura tem aquele nome e nascimento.
--  - Câmara e Senado ligados entre si dão a mesma pessoa (a identidade funde as duas chaves).
--  - A candidatura do TSE liga-se à pessoa (a âncora é o registro da Câmara, ou do Senado se não houver).
-- Quem não passa na regra não é ligado; os testes `vinculos_ambiguos` e `eleitos_federais_sem_vinculo` medem isso.
with pessoas as (

    select *

    from {{ ref('int_pessoas_para_vinculo') }}

    where nome_chave is not null and nascimento is not null

),

chaves as (

    select
        nome_chave,
        nascimento,
        max(id_na_fonte) filter (where fonte = '{{ var("source_camara") }}') as id_camara,
        max(id_na_fonte) filter (where fonte = '{{ var("source_senado") }}') as id_senado

    from pessoas

    group by nome_chave, nascimento

    having count(*) filter (where fonte = '{{ var("source_camara") }}') <= 1
       and count(*) filter (where fonte = '{{ var("source_senado") }}') <= 1

),

candidaturas as (

    select
        ano_eleicao,
        candidatura_id,
        name_key(nome) as nome_chave,
        nascimento

    from {{ ref('stg_tse__candidaturas') }}

    where nome is not null and nascimento is not null

    qualify count(distinct candidatura_id) over (partition by ano_eleicao, name_key(nome), nascimento) = 1

)

select
    '{{ var("source_camara") }}' as origem_fonte,
    '{{ var("id_type_camara") }}' as origem_tipo,
    id_camara as origem_id,
    '{{ var("source_senado") }}' as destino_fonte,
    '{{ var("id_type_senado") }}' as destino_tipo,
    id_senado as destino_id,
    'nome civil e data de nascimento iguais e únicos' as metodo

from chaves

where id_camara is not null and id_senado is not null

union all

select distinct
    '{{ var("source_tse") }}',
    '{{ var("id_type_tse") }}',
    c.candidatura_id,
    if(k.id_camara is not null, '{{ var("source_camara") }}', '{{ var("source_senado") }}'),
    if(k.id_camara is not null, '{{ var("id_type_camara") }}', '{{ var("id_type_senado") }}'),
    coalesce(k.id_camara, k.id_senado),
    'nome civil e data de nascimento iguais e únicos'

from candidaturas as c

inner join chaves as k on k.nome_chave = c.nome_chave and k.nascimento = c.nascimento
