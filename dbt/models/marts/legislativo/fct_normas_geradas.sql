-- Norma jurídica que resultou de uma matéria. Só o Senado informa (no processo); a Câmara fica para depois.
select
    '{{ var("source_senado") }}' as fonte,
    cast(p.id_materia as varchar) as id_proposicao,
    p.id_norma,
    p.norma_tipo as tipo,
    p.norma_numero as numero,
    p.norma_ano as ano,
    p.dt_norma_assinatura as dt_assinatura,
    p.dt_norma_publicacao as dt_publicacao,
    p.norma_descricao as descricao,
    p.norma_veiculo as veiculo_publicacao,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__processos') }} as p

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = p.id_captura

where p.norma_descricao is not null
