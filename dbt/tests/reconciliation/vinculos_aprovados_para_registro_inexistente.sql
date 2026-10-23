-- Erro se um vínculo aprovado à mão aponta para um registro que não existe (digitação errada).
-- A origem do TSE é a candidatura (staging); a da Câmara e a do Senado é o registro visto nos dados.
select v.origem_fonte, v.origem_id, v.destino_fonte, v.destino_id
from {{ ref('vinculos_aprovados') }} as v
where not exists (
        select 1 from {{ ref('int_pessoas_ids_vistos') }} as p
        where p.fonte = v.destino_fonte and p.id_na_fonte = v.destino_id
    )
    or (v.origem_fonte = '{{ var("source_tse") }}' and not exists (
        select 1 from {{ ref('stg_tse__candidaturas') }} as c where c.candidatura_id = v.origem_id
    ))
    or (v.origem_fonte <> '{{ var("source_tse") }}' and not exists (
        select 1 from {{ ref('int_pessoas_ids_vistos') }} as p
        where p.fonte = v.origem_fonte and p.id_na_fonte = v.origem_id
    ))
