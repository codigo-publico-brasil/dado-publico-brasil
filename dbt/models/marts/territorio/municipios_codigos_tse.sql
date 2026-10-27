-- De-para entre o código de município do TSE (`ue` das eleições municipais) e o código do IBGE. O TSE não publica o
-- código do IBGE, então a ligação é por nome e UF (sem acento, caixa nem pontuação), e só vale quando o par é único dos
-- dois lados. Quem não liga fica com `id_municipio` vazio, e o teste `municipios_do_tse_sem_correspondencia_no_ibge`
-- mede quantos são.
with candidaturas as (

    select ue, uf, ue_nome, ano_eleicao, count(*) as qtd

    from {{ ref('stg_tse__candidaturas') }}

    where regexp_matches(ue, '^[0-9]+$')

    group by all

),

-- um código de município tem uma UF só; se o arquivo de algum ano traz outra (erro da fonte, como 5 linhas de Abaeté
-- com UF de outro estado em 2000), vale a UF com mais candidaturas
tse as (

    select
        ue as cd_municipio_tse,
        arg_max(ue_nome, ano_eleicao) as nome_tse,
        arg_max(uf, qtd) as uf

    from candidaturas

    group by ue

),

chaves_tse as (

    select *, regexp_replace(name_key(nome_tse), '[^a-z0-9]', '', 'g') as chave from tse

),

chaves_ibge as (

    select id_municipio, uf, regexp_replace(name_key(nome), '[^a-z0-9]', '', 'g') as chave

    from {{ ref('stg_ibge__municipios') }}

),

unicos_tse as (

    select uf, chave from chaves_tse group by uf, chave having count(*) = 1

),

unicos_ibge as (

    select uf, chave, any_value(id_municipio) as id_municipio from chaves_ibge group by uf, chave having count(*) = 1

)

select
    'tse' as fonte,
    t.cd_municipio_tse,
    t.nome_tse,
    t.uf,
    i.id_municipio,
    if(i.id_municipio is not null, 'nome e UF iguais e únicos', null) as metodo

from chaves_tse as t

left join unicos_tse as u on u.uf = t.uf and u.chave = t.chave

left join unicos_ibge as i on u.chave is not null and i.uf = t.uf and i.chave = t.chave
