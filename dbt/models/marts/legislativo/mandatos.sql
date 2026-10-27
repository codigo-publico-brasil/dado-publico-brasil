-- Um mandato por pessoa e legislatura em que há voto registrado (no Senado, só nas legislaturas de um exercício oficial,
-- para quem o tem). Início e fim vêm do exercício oficial
-- quando a fonte publica: o Senado (`mandatos_exercicios`) e o histórico dos deputados da Câmara. As datas do
-- primeiro e do último voto são só o observado e as da legislatura são as oficiais dela.
with votos as (

    select
        v.fonte,
        v.id_pessoa,
        if(v.fonte = '{{ var("source_senado") }}', 'Senador', 'Deputado federal') as cargo,
        if(v.fonte = '{{ var("source_senado") }}', 'Senado Federal', 'Câmara dos Deputados') as casa,
        v.id_legislatura,
        arg_max(v.uf_sigla, v.dt_voto) as uf,
        min(v.dt_voto) as dt_primeiro_voto_observado,
        max(v.dt_voto) as dt_ultimo_voto_observado,
        any_value(l.dt_inicio) as dt_legislatura_inicio,
        any_value(l.dt_fim) as dt_legislatura_fim

    from {{ ref('int_votacoes_votos_ligados') }} as v

    left join {{ ref('stg_camara__legislaturas') }} as l on l.id_legislatura = v.id_legislatura

    where v.id_legislatura is not null

    group by v.fonte, v.id_pessoa, v.id_legislatura

),

-- Senado: exercícios que tocam a legislatura; fim vazio se algum ainda está em curso.
-- Câmara: posse (primeiro registro em exercício) e fim de mandato (registro FIM_MANDATO) do histórico do deputado.
exercicios as (

    select
        m.id_pessoa,
        m.id_legislatura,
        min(e.dt_inicio) as dt_inicio,
        if(bool_or(e.dt_fim is null), null, max(e.dt_fim)) as dt_fim

    from votos as m

    inner join {{ ref('mandatos_exercicios') }} as e
        on e.id_pessoa = m.id_pessoa
        and e.dt_inicio <= m.dt_legislatura_fim
        and coalesce(e.dt_fim, date '9999-12-31') >= m.dt_legislatura_inicio

    where m.fonte = '{{ var("source_senado") }}'

    group by m.id_pessoa, m.id_legislatura

    union all

    select
        i.id_pessoa,
        h.id_legislatura,
        cast(min(h.dt_registro) filter (where h.situacao = 'Exercício') as date) as dt_inicio,
        cast(max(h.dt_registro) filter (where h.situacao = 'FIM_MANDATO') as date) as dt_fim

    from {{ ref('stg_camara__deputados_historico') }} as h

    inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
        on i.fonte = '{{ var("source_camara") }}'
        and i.id_tipo = '{{ var("id_type_camara") }}'
        and i.id_na_fonte = cast(h.id_deputado as varchar)

    group by i.id_pessoa, h.id_legislatura

)

select
    v.fonte,
    v.id_pessoa,
    v.cargo,
    v.casa,
    v.id_legislatura,
    v.uf,
    x.dt_inicio,
    x.dt_fim,
    v.dt_primeiro_voto_observado,
    v.dt_ultimo_voto_observado,
    if(x.dt_inicio is not null, 'exercício oficial', 'votos observados') as base,
    v.dt_legislatura_inicio,
    v.dt_legislatura_fim

from votos as v

left join exercicios as x on x.id_pessoa = v.id_pessoa and x.id_legislatura = v.id_legislatura

-- O Senado carimba datas impossíveis em algumas votações antigas (a de 1999 a 2003 sai com 2015; ver a issue #100). Quem tem
-- exercício oficial só tem mandato nas legislaturas desses exercícios; o voto de data impossível não cria mandato.
where not (
    v.fonte = '{{ var("source_senado") }}'
    and x.dt_inicio is null
    and exists (select 1 from {{ ref('mandatos_exercicios') }} as e where e.id_pessoa = v.id_pessoa)
)
