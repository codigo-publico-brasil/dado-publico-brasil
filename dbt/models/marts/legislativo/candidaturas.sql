-- Candidaturas ao Congresso de quem já é pessoa do projeto (deputado ou senador ligado pela regra de ADR 0013).
-- As demais candidaturas ficam só no staging: não há página de quem não foi eleito.
select
    '{{ var("source_tse") }}' as fonte,
    i.id_pessoa,
    c.candidatura_id,
    c.ano_eleicao,
    c.turno,
    c.uf,
    c.cargo,
    c.numero,
    c.nome_urna,
    c.partido_sigla as partido,
    c.partido_nome,
    c.situacao_candidatura,
    c.resultado,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_tse__candidaturas') }} as c

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.tipo_id = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = c.candidatura_id

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = c.source_file_id
