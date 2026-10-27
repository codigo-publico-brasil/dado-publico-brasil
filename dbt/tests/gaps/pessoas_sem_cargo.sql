{{ config(severity='warn') }}
-- Pessoa que não é parlamentar da Câmara ou do Senado nem tem candidatura eleita: não deveria existir em core.pessoas
-- (a regra é "quem já teve pelo menos um cargo", ADR 0031). Zero é o esperado.
select p.id_pessoa
from {{ ref('core_pessoas') }} as p
where not exists (
        select 1 from {{ ref('stg_identity__pessoa_identificadores') }} as i
        where i.id_pessoa = p.id_pessoa and i.fonte in ('{{ var("source_camara") }}', '{{ var("source_senado") }}')
    )
    and not exists (
        select 1
        from {{ ref('stg_identity__pessoa_identificadores') }} as i
        inner join {{ ref('fatos_mandatos') }} as m on m.id_candidatura = i.id_na_fonte
        where i.id_pessoa = p.id_pessoa and i.fonte = '{{ var("source_tse") }}'
    )
