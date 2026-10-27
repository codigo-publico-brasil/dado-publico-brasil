-- Cada candidatura de uma eleição, como o TSE registrou, SÓ com arquivos do TSE: quem era, por qual partido, em que
-- disputa, o desfecho e o que declarou na campanha. Uma linha por candidatura (os turnos estão em `eleicoes_resultados`),
-- de todos os cargos menos vereador. A mesma pessoa em eleições diferentes é achada por `id_pessoa_tse` (nome civil ou de
-- urna e nascimento únicos, ADRs 0025 e 0026); sem ela a candidatura não tem histórico, e isso não quer dizer novato.
-- Os totais da campanha ficam vazios (e não zero) quando o arquivo ainda não foi carregado ou não traz o candidato.
with turnos as (

    select
        id_candidatura,
        max(turno) as qtd_turnos,
        arg_max(situacao_candidatura, turno) as situacao_candidatura,
        arg_max(resultado, turno) as resultado,
        bool_or(resultado like 'Eleito%') as fl_eleito,
        max(id_captura) as id_captura

    from {{ ref('stg_tse__candidaturas') }}

    group by id_candidatura

),

ultimo_turno as (

    -- o mais votado do último turno com votos, para a disputa de uma vaga (derivado dos votos, ver `eleicoes_resultados`)
    select id_candidatura, fl_mais_votado_no_turno

    from {{ ref('eleicoes_resultados') }}

    where fl_mais_votado_no_turno is not null

    qualify row_number() over (partition by id_candidatura order by turno desc) = 1

),

bens as (

    select id_candidatura, count(*) as qtd_bens, sum(valor) as valor_bens from {{ ref('stg_tse__bens') }} group by 1

),

receitas as (

    select id_candidatura, count(*) as qtd_receitas, sum(valor) as valor_receitas, max(dt_prestacao) as dt_prestacao
    from {{ ref('stg_tse__receitas_candidatos') }} group by 1

),

despesas as (

    select id_candidatura, count(*) as qtd_despesas, sum(valor) as valor_despesas, max(dt_prestacao) as dt_prestacao
    from {{ ref('stg_tse__despesas_candidatos') }} group by 1

),

fotos as (

    -- a foto oficial da candidatura no pacote do TSE (uma por candidato e eleição)
    select ano_eleicao, sq_candidato, pacote_uf, arquivo

    from {{ ref('stg_tse__fotos') }}

    qualify row_number() over (partition by ano_eleicao, sq_candidato order by arquivo) = 1

),

cadastro as (

    -- dados de cadastro da candidatura (iguais nos turnos): vale o primeiro turno
    select distinct on (id_candidatura)
        id_candidatura, ano_eleicao, cd_eleicao, eleicao, uf, ue, ue_nome, cargo, sq_candidato, numero, nome, nome_urna,
        nome_social, genero, grau_instrucao, estado_civil, ocupacao, partido_sigla, partido_nome, federacao_sigla,
        coligacao_nome

    from {{ ref('stg_tse__candidaturas') }}

    order by id_candidatura, turno

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    c.ano_eleicao,
    c.cd_eleicao,
    c.eleicao,
    c.uf,
    c.ue,
    c.ue_nome,
    c.cargo,
    c.sq_candidato,
    c.numero,
    c.nome,
    c.nome_urna,
    c.nome_social,
    c.genero,
    c.grau_instrucao,
    c.estado_civil,
    c.ocupacao,
    c.partido_sigla as partido,
    c.partido_nome,
    c.federacao_sigla as federacao,
    c.coligacao_nome as coligacao,
    t.situacao_candidatura,
    t.qtd_turnos,
    t.resultado,
    t.fl_eleito,
    u.fl_mais_votado_no_turno as fl_mais_votado_no_ultimo_turno,
    p.id_pessoa_tse,
    f.arquivo as foto_arquivo,
    if(
        f.arquivo is not null,
        c.ano_eleicao || '/' || f.pacote_uf || '/' || c.sq_candidato || '.' || regexp_extract(f.arquivo, '[.](jpe?g)$', 1),
        null
    ) as foto_caminho,
    if(
        f.arquivo is not null,
        'https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes' || c.ano_eleicao || '/fotos/foto_cand' || c.ano_eleicao
        || '_' || f.pacote_uf || '_div.zip',
        null
    ) as foto_pacote_url,
    cast(b.qtd_bens as bigint) as qtd_bens,
    cast(b.valor_bens as decimal(18, 2)) as valor_bens,
    cast(r.qtd_receitas as bigint) as qtd_receitas,
    cast(r.valor_receitas as decimal(18, 2)) as valor_receitas,
    cast(d.qtd_despesas as bigint) as qtd_despesas,
    cast(d.valor_despesas as decimal(18, 2)) as valor_despesas,
    greatest(r.dt_prestacao, d.dt_prestacao) as dt_prestacao,
    cast(k.dt_captura as date) as dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || c.ano_eleicao as fonte_url

from cadastro as c

inner join turnos as t on t.id_candidatura = c.id_candidatura

left join ultimo_turno as u on u.id_candidatura = c.id_candidatura

left join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

left join fotos as f on f.ano_eleicao = c.ano_eleicao and f.sq_candidato = c.sq_candidato

left join bens as b on b.id_candidatura = c.id_candidatura

left join receitas as r on r.id_candidatura = c.id_candidatura

left join despesas as d on d.id_candidatura = c.id_candidatura

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = t.id_captura

where c.cargo <> 'Vereador'
