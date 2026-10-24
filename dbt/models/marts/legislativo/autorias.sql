-- Uma linha por autor e proposição. O autor que não é deputado (comissão, Senado, Executivo...) fica, sem id_pessoa.
with totais as (

    select proposicao_id, count(*) as qtd_autores

    from {{ ref('int_autorias_ligadas_a_pessoas') }}

    group by proposicao_id

)

select
    a.id_pessoa,
    '{{ var("source_camara") }}' as fonte,
    cast(a.proposicao_id as varchar) as proposicao_id,
    a.ordem_assinatura,
    t.qtd_autores,
    a.nome_autor,
    a.tipo_autor,
    a.proponente,
    '{{ var("url_proposicao_camara") }}' || cast(a.proposicao_id as varchar) as proposicao_fonte_url

from {{ ref('int_autorias_ligadas_a_pessoas') }} as a

inner join totais as t on t.proposicao_id = a.proposicao_id
