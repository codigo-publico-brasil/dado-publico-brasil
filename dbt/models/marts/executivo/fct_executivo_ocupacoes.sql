-- Quem exerceu Presidente, Vice-Presidente e Ministro de Estado, e quando, como a CGU publica (PEP). A fonte só guarda os
-- últimos cinco anos, então o histórico anterior a 2019 não existe aqui. Cada mês capturado repete as mesmas linhas: vale a
-- captura mais recente de cada pessoa, função, órgão e início, e o que saiu da foto mais nova continua, vindo da anterior.
-- Sem CPF nem data de nascimento na fonte, a pessoa não é ligada a `dim_pessoas`: o nome fica como a fonte publica.
with chaves as (

select
    md5(concat_ws('|', nome, funcao, orgao, coalesce(cast(dt_inicio as varchar), ''))) as id_ocupacao_executivo,
    *

from {{ ref('stg_pep__dirigentes') }}

)

select
    fonte,
    id_ocupacao_executivo,
    nome,
    funcao,
    orgao,
    dt_inicio,
    dt_fim,
    dt_fim_carencia,
    url_fonte,
    id_captura,
    cast(dt_captura as date) as dt_captura

from chaves

qualify row_number() over (partition by id_ocupacao_executivo order by dt_captura desc, id_captura desc) = 1
