-- Um mandato por pessoa e legislatura em que há voto registrado. A fonte não informa início e fim do
-- mandato de cada pessoa (suplentes entram e saem no meio da legislatura), então ficam vazios; as datas
-- do primeiro e do último voto são só o observado e as da legislatura são as oficiais dela.
select
    v.fonte,
    v.id_pessoa,
    if(v.fonte = '{{ var("source_senado") }}', 'Senador', 'Deputado federal') as cargo,
    if(v.fonte = '{{ var("source_senado") }}', 'Senado Federal', 'Câmara dos Deputados') as casa,
    v.legislatura_id,
    arg_max(v.uf_sigla, v.votou_em) as uf,
    cast(null as date) as inicio,
    cast(null as date) as fim,
    min(v.votou_em) as primeiro_voto_observado_em,
    max(v.votou_em) as ultimo_voto_observado_em,
    'votos observados' as base,
    any_value(l.inicio) as legislatura_inicio,
    any_value(l.fim) as legislatura_fim

from {{ ref('int_votos_ligados_a_pessoas') }} as v

left join {{ ref('stg_camara__legislaturas') }} as l on l.legislatura_id = v.legislatura_id

where v.legislatura_id is not null

group by v.fonte, v.id_pessoa, v.legislatura_id
