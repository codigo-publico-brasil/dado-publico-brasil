-- Quem ocupa cada cargo, uma linha por mandato; o aplicativo filtra a data (dt_inicio <= data <= dt_fim_prevista) e o cargo.
-- Só leitura dos fatos e do núcleo. A composição eleita não é o exercício (cassação, renúncia e morte não entram no fim);
-- para quem de fato exerce, ver agg_composicoes e fct_exercicios. Sem data de posse (por exemplo, deputado estadual de 2026,
-- cuja data está nas constituições estaduais), o mandato entra com `dt_inicio` vazio e `ano_inicio` preenchido.
--
-- `tipo_mandato` compara o mandato com o anterior da mesma pessoa no mesmo cargo (e na mesma unidade, abaixo do nível
-- federal): reeleito se o anterior é da eleição de um mandato atrás, retorno se há um intervalo, novato se não há anterior
-- e a base de eleições já cobria o ciclo anterior (senão fica vazio: sem prova nada é afirmado).
with mandatos as (

    select
        m.*,
        cast(substr(m.id_eleicao, 1, 4) as integer) as ano_eleicao,
        c.nome as cargo,
        c.duracao_anos,
        c.esfera,
        c.id_cargo_titular

    from {{ ref('fct_mandatos') }} as m

    inner join {{ ref('dim_cargos') }} as c on c.id_cargo = m.id_cargo

),

anteriores as (

    select
        *,
        -- cada cargo conta à parte: quem foi titular e depois vice não é "reeleito"
        lag(ano_eleicao) over (
            partition by id_pessoa, id_cargo, if(esfera = 'federal', '', id_territorio)
            order by ano_eleicao
        ) as ano_anterior,
        min(ano_eleicao) over (partition by id_cargo) as primeiro_ano_do_cargo

    from mandatos

    where id_pessoa is not null

)

select
    m.id_candidatura,
    m.id_pessoa,
    p.nome_publico as nome,
    m.cargo,
    t.nome as territorio,
    pa.sigla as partido,
    m.ano_eleicao + 1 as ano_inicio,
    m.dt_inicio,
    m.base_dt_inicio as base_do_inicio,
    m.dt_fim_prevista,
    m.base_eleicao,
    case
        when m.ano_anterior is not null and m.ano_eleicao - m.ano_anterior = m.duracao_anos then 'reeleito'
        when m.ano_anterior is not null then 'retorno'
        when m.ano_eleicao - m.duracao_anos >= m.primeiro_ano_do_cargo then 'novato'
    end as tipo_mandato,
    cap.url as fonte_url,
    cast(cap.dt_captura as date) as dt_captura

from anteriores as m

inner join {{ ref('dim_pessoas') }} as p on p.id_pessoa = m.id_pessoa

left join {{ ref('dim_territorios') }} as t on t.id_territorio = m.id_territorio

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = m.id_partido

left join {{ ref('stg_metadata__captures') }} as cap on cap.id_captura = m.id_captura
