-- Quem ocupa cada cargo, uma linha por período de ocupação; o aplicativo filtra a data (dt_inicio <= data <= dt_fim_prevista)
-- e o cargo. Só junta nomes à ocupação (fct_cargos_ocupacoes), que traz a regra de exercício e mandato (ADR de ocupação).
select
    o.id_candidatura,
    o.id_pessoa,
    p.nome_publico as nome,
    c.nome as cargo,
    t.nome as territorio,
    pa.sigla as partido,
    o.ano_inicio,
    o.dt_inicio,
    o.base_dt_inicio as base_do_inicio,
    o.dt_fim as dt_fim_prevista,
    -- o contrato do aplicativo: informado ou derivado (a ocupação chama de previsto o fim derivado), sempre preenchido
    if(o.base_dt_fim = 'informado', 'informado', 'derivado') as base_do_fim,
    m.base_eleicao,
    fc.dt_eleicao,
    m.tipo_mandato,
    o.base_ocupacao as tipo_registro,
    cap.url as fonte_url,
    o.dt_captura

from {{ ref('fct_cargos_ocupacoes') }} as o

inner join {{ ref('dim_pessoas') }} as p on p.id_pessoa = o.id_pessoa

-- sem cargo (mandato de candidatura sem disputa) a ocupação não entra, como sempre foi
inner join {{ ref('dim_cargos') }} as c on c.id_cargo = o.id_cargo

left join {{ ref('dim_territorios') }} as t on t.id_territorio = o.id_territorio

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = o.id_partido

left join {{ ref('fct_mandatos') }} as m on m.id_candidatura = o.id_candidatura

left join {{ ref('fct_candidaturas') }} as fc on fc.id_candidatura = o.id_candidatura

left join {{ ref('stg_metadata__capturas') }} as cap on cap.id_captura = o.id_captura
