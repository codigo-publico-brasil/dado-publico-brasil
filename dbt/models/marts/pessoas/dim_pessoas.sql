
-- Quem já teve pelo menos um cargo (ADR 0030 e 0031): parlamentar da Câmara ou do Senado, e todo eleito do TSE, a
-- partir do momento da eleição. Uma linha por pessoa do projeto (chave `identity`, nunca reaproveitada). Cada atributo
-- diz de qual fonte veio: a Câmara e o Senado valem mais que o TSE, e o TSE vale a candidatura mais recente que o traz.
-- Só atributos que a fonte publica; nada é inferido nem completado. Gênero só quando a fonte diz masculino ou feminino.
with oficiais as (

    select id_pessoa, fonte, nome, nome_civil, sexo, dt_nascimento
    from {{ ref('int_pessoas_unidas_cadastro') }}

    union all

    select id_pessoa, fonte, nome, nome_civil, sexo, dt_nascimento
    from {{ ref('int_pessoas_senado_unidas') }}

),

oficial as (

    -- depois da fusão a pessoa pode estar nas duas casas: os dados da Câmara vencem
    select *
    from oficiais
    qualify row_number() over (partition by id_pessoa order by if(fonte = '{{ var("source_camara") }}', 0, 1)) = 1

),

tse as (

    select
        i.id_pessoa,
        c.nome,
        c.nome_urna,
        c.dt_nascimento,
        case lower(c.genero) when 'masculino' then 'masculino' when 'feminino' then 'feminino' end as genero,
        c.ano_eleicao

    from {{ ref('stg_identity__pessoa_identificadores') }} as i

    inner join {{ ref('stg_tse__candidaturas') }} as c
        on i.fonte = '{{ var("source_tse") }}' and i.id_tipo = '{{ var("id_type_tse_eleito") }}' and i.id_na_fonte = c.id_candidatura

),

tse_atual as (

    -- cada atributo vem da candidatura mais recente que o traz (o nascimento pode faltar numa e constar noutra)
    select
        id_pessoa,
        arg_max(nome, ano_eleicao) filter (where nome is not null) as nome_civil,
        arg_max(nome_urna, ano_eleicao) filter (where nome_urna is not null) as nome_urna,
        arg_max(dt_nascimento, ano_eleicao) filter (where dt_nascimento is not null) as dt_nascimento,
        arg_max(genero, ano_eleicao) filter (where genero is not null) as genero

    from tse

    group by id_pessoa

)

select
    p.id_pessoa,
    coalesce(o.nome_civil, t.nome_civil) as nome_civil,
    if(o.nome_civil is not null, o.fonte, if(t.nome_civil is not null, '{{ var("source_tse") }}', null)) as fonte_nome_civil,
    coalesce(o.nome, t.nome_urna) as nome_publico,
    if(o.nome is not null, o.fonte, if(t.nome_urna is not null, '{{ var("source_tse") }}', null)) as fonte_nome_publico,
    coalesce(o.dt_nascimento, t.dt_nascimento) as dt_nascimento,
    if(o.dt_nascimento is not null, o.fonte, if(t.dt_nascimento is not null, '{{ var("source_tse") }}', null)) as fonte_dt_nascimento,
    coalesce(
        case o.sexo when 'M' then 'masculino' when 'F' then 'feminino' end, t.genero
    ) as genero,
    if(
        case o.sexo when 'M' then 'masculino' when 'F' then 'feminino' end is not null,
        o.fonte,
        if(t.genero is not null, '{{ var("source_tse") }}', null)
    ) as fonte_genero,
    cast(p.dt_criacao as date) as dt_entrada

from {{ ref('stg_identity__pessoas') }} as p

left join oficial as o on o.id_pessoa = p.id_pessoa

left join tse_atual as t on t.id_pessoa = p.id_pessoa
