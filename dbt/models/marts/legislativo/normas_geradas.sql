-- Norma jurídica que resultou de uma matéria. Só o Senado informa (no processo); a Câmara fica para depois.
select
    '{{ var("source_senado") }}' as fonte,
    cast(p.materia_id as varchar) as proposicao_id,
    p.norma_tipo as tipo,
    p.norma_numero as numero,
    p.norma_ano as ano,
    p.norma_assinada_em as assinada_em,
    p.norma_publicada_em as publicada_em,
    p.norma_descricao as descricao,
    p.norma_veiculo as veiculo_publicacao,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__processos') }} as p

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = p.source_file_id

where p.norma_descricao is not null
