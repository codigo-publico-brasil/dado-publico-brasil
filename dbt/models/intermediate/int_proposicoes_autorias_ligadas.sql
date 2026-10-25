-- Autor que não é deputado (comissão, Senado, Executivo...) fica sem pessoa (id_pessoa nulo).
select
    a.id_proposicao,
    a.ordem_assinatura,
    a.nome_autor,
    i.id_pessoa,
    a.tipo_autor,
    a.partido_sigla,
    a.uf_sigla,
    a.proponente,
    a.id_captura

from {{ ref('stg_camara__proposicoes_autores') }} as a

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(a.id_deputado as varchar)
