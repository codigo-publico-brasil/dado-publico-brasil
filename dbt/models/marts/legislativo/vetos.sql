-- Vetos presidenciais apreciados pelo Congresso, de 1994 em diante: a matéria vetada, a norma que ela gerou, a
-- mensagem do veto e as datas. Uma linha por veto.
select
    '{{ var("source_senado") }}' as fonte,
    v.veto_id,
    v.materia_veto_id,
    v.numero,
    v.ano,
    v.materia_vetada_id,
    v.materia_vetada_sigla,
    v.materia_vetada_numero,
    v.materia_vetada_ano,
    v.materia_vetada_ementa,
    v.norma_id,
    v.norma_nome,
    v.mensagem_numero,
    v.mensagem_ano,
    v.mensagem_url,
    v.veto_total,
    v.assunto,
    v.recebido_em,
    v.publicado_em,
    v.sobrestado_em,
    v.sobrestando_pauta,
    v.quantidade_dispositivos,
    v.em_tramitacao,
    '{{ var("url_materia_senado") }}' || v.materia_veto_id as fonte_url,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__vetos') }} as v

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = v.source_file_id
