{{ config(severity='warn') }}
-- Grupos de candidaturas do TSE (mesma pessoa entre as eleições) que tocam mais de uma pessoa do projeto: a identidade
-- não os funde sozinha porque haveria duas pessoas oficiais (Câmara e Senado) ou porque a ligação é ambígua. Cada linha
-- é um caso para conferir à mão (vinculos_aprovados). Zero é o esperado.
select g.grupo, count(distinct i.id_pessoa) as qtd_pessoas
from {{ ref('int_tse_eleitos_grupos') }} as g
inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}' and i.id_tipo = '{{ var("id_type_tse_eleito") }}' and i.id_na_fonte = g.id_candidatura
group by g.grupo
having count(distinct i.id_pessoa) > 1
