-- Erro se alguma candidatura ligada a uma pessoa se perdeu entre a identidade e os marts (o mart tem uma linha
-- por turno, a identidade um identificador por candidatura: compara candidaturas distintas).
select 1
where (
    select count(*) from {{ ref('stg_identity__pessoa_identificadores') }} where fonte = '{{ var("source_tse") }}'
) <> (select count(distinct candidatura_id) from {{ ref('candidaturas') }})
