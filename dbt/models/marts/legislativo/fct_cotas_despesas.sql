-- Despesas da cota para o exercício da atividade parlamentar (CEAP da Câmara, CEAPS do Senado), uma linha por despesa
-- como a fonte publica: tipo, fornecedor, documento, datas e valores. Só fatos: sem total avaliativo nem ordenação entre
-- pessoas (ADR 0054). As duas casas medem valores de formas diferentes e as colunas ficam separadas (a Câmara traz
-- documento, glosa e líquido; o Senado, o valor reembolsado); nada é somado nem completado.
-- Pessoa (`id_pessoa`): na Câmara vem do identificador do deputado que a própria fonte publica (`informada`); no Senado a
-- fonte só traz o nome, e a pessoa é DERIVADA (ADR 0057): o nome, sem acento e caixa, é o nome parlamentar ou civil de UMA
-- só pessoa que exercia o cargo de senador no mês da despesa. Zero ou mais de uma: fica sem pessoa (nunca se escolhe
-- entre homônimos).
with senado as (

    select * from {{ ref('stg_senado__ceaps') }}

),

meses as (

    select distinct name_key(senador_nome) as nome_chave, make_date(ano, mes, 1) as dt_mes
    from senado
    where ano is not null and mes between 1 and 12

),

nomes_de_pessoas as (

    -- uma chave por nome, para ligar por igualdade (join por hash); `in (f(a), f(b))` ou `or` na condição vira produto cartesiano
    select id_pessoa, name_key(nome_publico) as chave, true as por_nome_parlamentar from {{ ref('dim_pessoas') }}

    union all

    select id_pessoa, name_key(nome_civil), false from {{ ref('dim_pessoas') }} where nome_civil is not null

),

candidatas as (

    select
        m.nome_chave,
        m.dt_mes,
        n.id_pessoa,
        n.por_nome_parlamentar

    from meses as m

    inner join nomes_de_pessoas as n on m.nome_chave = n.chave

    where exists (
        select 1 from {{ ref('fct_exercicios') }} as x
        where x.id_pessoa = n.id_pessoa
            and x.id_cargo = 'senador'
            and x.dt_inicio <= last_day(m.dt_mes)
            and coalesce(x.dt_fim, x.dt_mandato_fim, current_date) >= m.dt_mes
    )

),

ligadas as (

    select
        nome_chave,
        dt_mes,
        any_value(id_pessoa) as id_pessoa,
        if(bool_or(por_nome_parlamentar), 'nome_parlamentar_e_exercicio', 'nome_civil_e_exercicio') as regra

    from candidatas

    group by nome_chave, dt_mes

    having count(distinct id_pessoa) = 1

),

camara as (

    select
        c.fonte,
        md5(c.fonte || ':' || c.hash_linha) as id_despesa,
        i.id_pessoa,
        if(i.id_pessoa is not null, 'id_na_fonte', null) as regra_ligacao_pessoa,
        if(i.id_pessoa is not null, 'informada', null) as precisao_ligacao_pessoa,
        c.deputado_nome as nome_parlamentar,
        c.uf_sigla as uf,
        c.partido_sigla,
        c.ano,
        c.mes,
        c.subcota_descricao as tipo_despesa,
        c.especificacao_descricao as especificacao,
        c.fornecedor_nome as fornecedor,
        c.fornecedor_documento as documento_fornecedor,
        c.fl_fornecedor_pessoa_fisica,
        c.numero_documento,
        c.dt_emissao,
        c.valor_documento,
        c.valor_glosa,
        c.valor_liquido,
        cast(null as decimal(18, 2)) as valor_reembolsado,
        c.trecho,
        cast(null as varchar) as detalhamento,
        cast(c.id_documento as varchar) as id_documento,
        c.url_documento,
        c.id_captura,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('stg_camara__cota_parlamentar') }} as c

    left join {{ ref('stg_identity__pessoas_identificadores') }} as i
        on i.fonte = '{{ var("source_camara") }}'
        and i.id_tipo = '{{ var("id_type_camara") }}'
        and i.id_na_fonte = cast(c.id_deputado as varchar)

),

senadores as (

    select
        s.fonte,
        md5(s.fonte || ':' || s.hash_linha) as id_despesa,
        l.id_pessoa,
        l.regra as regra_ligacao_pessoa,
        if(l.id_pessoa is not null, 'derivada', null) as precisao_ligacao_pessoa,
        s.senador_nome as nome_parlamentar,
        cast(null as varchar) as uf,
        cast(null as varchar) as partido_sigla,
        s.ano,
        s.mes,
        s.tipo_despesa,
        cast(null as varchar) as especificacao,
        s.fornecedor_nome as fornecedor,
        s.fornecedor_documento as documento_fornecedor,
        s.fl_fornecedor_pessoa_fisica,
        s.numero_documento,
        s.dt_emissao,
        cast(null as decimal(18, 2)) as valor_documento,
        cast(null as decimal(18, 2)) as valor_glosa,
        cast(null as decimal(18, 2)) as valor_liquido,
        s.valor_reembolsado,
        cast(null as varchar) as trecho,
        s.detalhamento,
        cast(s.id_documento as varchar) as id_documento,
        cast(null as varchar) as url_documento,
        s.id_captura,
        cast(s.dt_captura as date) as dt_captura

    from senado as s

    left join ligadas as l on l.nome_chave = name_key(s.senador_nome) and l.dt_mes = make_date(s.ano, s.mes, 1)

)

select * from camara
union all
select * from senadores
