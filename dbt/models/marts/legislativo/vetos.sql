-- Vetos presidenciais apreciados pelo Congresso, de 1994 em diante: a matéria vetada, a norma que ela gerou, a
-- mensagem do veto e as datas. Uma linha por veto.
select
    '{{ var("source_senado") }}' as fonte,
    v.id_veto,
    v.id_materia_veto,
    v.numero,
    v.ano,
    v.id_materia_vetada,
    v.materia_vetada_sigla,
    v.materia_vetada_numero,
    v.materia_vetada_ano,
    v.materia_vetada_ementa,
    v.id_norma,
    v.norma_nome,
    v.mensagem_numero,
    v.mensagem_ano,
    v.mensagem_url,
    v.fl_veto_total,
    v.assunto,
    v.dt_recebimento,
    v.dt_publicacao,
    v.dt_sobrestamento,
    v.fl_sobrestando_pauta,
    v.quantidade_dispositivos,
    v.fl_em_tramitacao,
    '{{ var("url_materia_senado") }}' || v.id_materia_veto as fonte_url,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__vetos') }} as v

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = v.id_captura
