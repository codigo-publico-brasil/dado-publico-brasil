-- Um mandato por pessoa e legislatura em que há voto registrado. A fonte não informa início e fim do
-- mandato de cada pessoa (suplentes entram e saem no meio da legislatura), então ficam vazios; as datas
-- do primeiro e do último voto são só o observado e as da legislatura são as oficiais dela.
select
    v.fonte,
    v.id_pessoa,
    if(v.fonte = '{{ var("source_senado") }}', 'Senador', 'Deputado federal') as cargo,
    if(v.fonte = '{{ var("source_senado") }}', 'Senado Federal', 'Câmara dos Deputados') as casa,
    v.id_legislatura,
    arg_max(v.uf_sigla, v.dt_voto) as uf,
    cast(null as date) as dt_inicio,
    cast(null as date) as dt_fim,
    min(v.dt_voto) as dt_primeiro_voto_observado,
    max(v.dt_voto) as dt_ultimo_voto_observado,
    'votos observados' as base,
    any_value(l.dt_inicio) as dt_legislatura_inicio,
    any_value(l.dt_fim) as dt_legislatura_fim

from {{ ref('int_votacoes_votos_ligados') }} as v

left join {{ ref('stg_camara__legislaturas') }} as l on l.id_legislatura = v.id_legislatura

where v.id_legislatura is not null

group by v.fonte, v.id_pessoa, v.id_legislatura
