-- Bens declarados por candidatos que já são pessoa do projeto (a candidatura ligada pela regra do ADR 0013), um por
-- linha. Os de outros candidatos ficam só no staging. O valor é o declarado à Justiça Eleitoral, sem correção.
select distinct
    '{{ var("source_tse") }}' as fonte,
    i.id_pessoa,
    b.candidatura_id,
    b.ano_eleicao,
    b.ordem,
    b.tipo,
    b.descricao,
    b.valor,
    b.atualizado_em,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_tse__bens') }} as b

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.tipo_id = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = b.candidatura_id

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = b.source_file_id
