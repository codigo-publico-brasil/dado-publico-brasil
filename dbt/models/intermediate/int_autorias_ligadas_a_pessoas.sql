-- Autor que não é deputado (comissão, Senado, Executivo...) fica sem pessoa (id_pessoa nulo).
select
    a.proposicao_id,
    a.ordem_assinatura,
    a.nome_autor,
    i.id_pessoa,
    a.tipo_autor,
    a.partido_sigla,
    a.uf_sigla,
    a.proponente,
    a.source_file_id

from {{ ref('stg_camara__proposicoes_autores') }} as a

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(a.deputado_id as varchar)
