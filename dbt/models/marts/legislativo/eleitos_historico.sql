-- As candidaturas anteriores de cada eleito, de qualquer cargo, quando a mesma pessoa é achada nas eleições do TSE
-- (nome civil e data de nascimento iguais e únicos, ADR 0025). Uma linha por eleito, eleição e cargo, pelo último turno.
-- Só entra quem foi eleito: não há página de quem só concorreu. Sem ligação, o eleito não tem linhas aqui (e a ficha
-- diz que o histórico não está confirmado, nunca que a pessoa é novata). O TSE não registra afastamentos.
select
    '{{ var("source_tse") }}' as fonte,
    e.id_candidatura,
    c.ano_eleicao,
    c.turno,
    c.uf,
    c.ue,
    c.ue_nome,
    c.cargo,
    c.partido_sigla as partido,
    c.situacao_candidatura,
    c.resultado,
    cast(k.dt_captura as date) as dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || c.ano_eleicao as fonte_url

from {{ ref('eleitos') }} as e

inner join {{ ref('int_tse_pessoas') }} as pe on pe.id_candidatura = e.id_candidatura

inner join {{ ref('int_tse_pessoas') }} as pa
    on pa.id_pessoa_tse = pe.id_pessoa_tse and pa.id_candidatura <> e.id_candidatura

inner join {{ ref('stg_tse__candidaturas') }} as c on c.id_candidatura = pa.id_candidatura

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = c.id_captura

where c.ano_eleicao < e.ano_eleicao

qualify row_number() over (partition by e.id_candidatura, c.ano_eleicao, c.cargo order by c.turno desc) = 1
