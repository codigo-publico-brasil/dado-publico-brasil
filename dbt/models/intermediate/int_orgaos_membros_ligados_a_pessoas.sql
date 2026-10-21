-- Membro de órgão ligado à pessoa do projeto; quem não está no cadastro de deputados fica de fora
-- (o teste membros_de_orgaos_de_deputado_nao_cadastrado mede isso).

select
    s.*,
    i.id_pessoa

from {{ ref('stg_camara__orgaos_membros') }} as s

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(s.deputado_id as varchar)
