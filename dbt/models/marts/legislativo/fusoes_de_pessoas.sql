-- Quando duas chaves de pessoa se mostram a mesma pessoa, a mais nova é absorvida pela mais antiga. Quem
-- guardou a chave antiga resolve a atual por aqui.
select
    id_pessoa_absorvida,
    id_pessoa_sobrevivente,
    metodo,
    fundida_em

from {{ ref('stg_identity__pessoa_fusoes') }}
