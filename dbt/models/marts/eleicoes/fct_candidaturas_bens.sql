-- Bens declarados por candidatos que já são pessoa do projeto (a candidatura ligada pela regra do ADR 0013), um por
-- linha. Os de outros candidatos ficam só no staging. O valor é o declarado à Justiça Eleitoral, sem correção.
select distinct
    '{{ var("source_tse") }}' as fonte,
    i.id_pessoa,
    b.id_candidatura,
    b.ano_eleicao,
    b.ordem,
    b.tipo,
    b.descricao,
    b.valor,
    b.dt_atualizacao,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_tse__bens') }} as b

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.id_tipo = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = b.id_candidatura

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = b.id_captura
