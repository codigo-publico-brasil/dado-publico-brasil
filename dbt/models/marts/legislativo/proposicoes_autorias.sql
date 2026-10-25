-- Uma linha por autor e proposição. O autor que não é deputado (comissão, Senado, Executivo...) fica, sem id_pessoa.
with totais as (

    select id_proposicao, count(*) as qtd_autores

    from {{ ref('int_proposicoes_autorias_ligadas') }}

    group by id_proposicao

)

select
    a.id_pessoa,
    '{{ var("source_camara") }}' as fonte,
    cast(a.id_proposicao as varchar) as id_proposicao,
    a.ordem_assinatura,
    t.qtd_autores,
    a.nome_autor,
    a.tipo_autor,
    a.proponente,
    '{{ var("url_proposicao_camara") }}' || cast(a.id_proposicao as varchar) as proposicao_fonte_url

from {{ ref('int_proposicoes_autorias_ligadas') }} as a

inner join totais as t on t.id_proposicao = a.id_proposicao
