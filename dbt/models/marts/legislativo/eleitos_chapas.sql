-- Vice e suplentes de quem foi eleito presidente, governador ou senador (ADR 0023): uma linha por integrante da chapa
-- que o TSE registra junto com o titular. Na chapa majoritária o vice e os suplentes usam o mesmo número do titular, na
-- mesma unidade eleitoral, eleição e turno; é por essa chave que se ligam. O vice e o suplente não são o eleito: assumem
-- o cargo só em vacância, e o resultado é o que o TSE informa na data da captura (provisório até a diplomação). Só
-- entra quem o TSE marca como eleito na chapa; o candidato substituído antes da eleição não entra.
with titulares as (

    select ano_eleicao, turno, ue, numero, cargo, id_candidatura

    from {{ ref('stg_tse__candidaturas') }}

    where resultado like 'Eleito%' and cargo in ('Presidente', 'Governador', 'Senador')

    -- vale o turno final, como em `eleitos`
    qualify row_number() over (partition by id_candidatura order by turno desc) = 1

),

integrantes as (

    select
        c.*,
        case c.cargo
            when 'Vice-presidente' then 'Presidente'
            when 'Vice-governador' then 'Governador'
            when '1º suplente' then 'Senador'
            when '2º suplente' then 'Senador'
        end as cargo_titular

    from {{ ref('stg_tse__candidaturas') }} as c

    -- só a chapa eleita: o candidato substituído (por exemplo, vice inapto trocado antes da eleição) mantém o número
    -- do titular, mas o TSE não lhe dá resultado de eleito
    where c.cargo in ('Vice-presidente', 'Vice-governador', '1º suplente', '2º suplente') and c.resultado like 'Eleito%'

)

select
    '{{ var("source_tse") }}' as fonte,
    t.id_candidatura as id_candidatura_titular,
    i.id_candidatura,
    t.ano_eleicao,
    i.turno,
    i.uf,
    i.ue,
    t.cargo as cargo_titular,
    i.cargo as papel,
    i.numero,
    i.nome,
    i.nome_urna,
    i.partido_sigla as partido,
    i.situacao_candidatura,
    i.resultado,
    cast(k.dt_captura as date) as dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || t.ano_eleicao as fonte_url

from titulares as t

inner join integrantes as i
    on i.ano_eleicao = t.ano_eleicao
    and i.turno = t.turno
    and i.ue = t.ue
    and i.numero = t.numero
    and i.cargo_titular = t.cargo

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = i.id_captura
