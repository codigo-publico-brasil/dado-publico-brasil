{{ config(alias='candidaturas') }}

-- Cada candidatura de uma eleição, como o TSE registrou, de todos os cargos (inclusive vereador): quem era, por qual
-- partido, em qual disputa, o desfecho e a foto oficial. SÓ arquivos do TSE (nada de Câmara, Senado nem pessoa do
-- projeto). Uma linha por candidatura; os turnos estão em `resultados` e a campanha em `campanhas`. A mesma pessoa em
-- eleições diferentes é achada por `id_pessoa_tse` (nome civil ou de urna e nascimento únicos, ADRs 0025 e 0026); sem ele a
-- candidatura não tem histórico, e isso não quer dizer novato. Só entram as eleições ordinárias (staging, issue 74).
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

    -- o mais votado do último turno com votos, para a disputa de uma vaga (derivado dos votos, ver `resultados`)
    select id_candidatura, fl_mais_votado_no_turno

    from {{ ref('resultados') }}

    where fl_mais_votado_no_turno is not null

    qualify row_number() over (partition by id_candidatura order by turno desc) = 1

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
        id_candidatura, ano_eleicao, cd_eleicao, ue, cargo, sq_candidato, numero, nome, nome_urna, nome_social, genero,
        grau_instrucao, estado_civil, ocupacao, partido_sigla, partido_nome, federacao_sigla, coligacao_nome

    from {{ ref('stg_tse__candidaturas') }}

    order by id_candidatura, turno

),

-- a disputa vem do arquivo de vagas; o cargo do arquivo de candidaturas é texto, então liga por nome sem acento nem pontuação
vagas as (

    select
        d.id_disputa,
        d.id_eleicao,
        d.ue,
        lower(regexp_replace(strip_accents(v.cargo), '[^a-zA-Z0-9]', '', 'g')) as chave_cargo

    from {{ ref('stg_tse__vagas') }} as v

    inner join {{ ref('cargos') }} as k on k.cd_cargo_tse = v.cd_cargo

    inner join {{ ref('disputas') }} as d
        on d.id_eleicao = v.ano_eleicao || '-' || v.cd_eleicao and d.ue = v.ue and d.id_cargo = k.id_cargo

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    v.id_disputa,
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
    t.id_captura

from cadastro as c

inner join turnos as t on t.id_candidatura = c.id_candidatura

left join vagas as v
    on v.id_eleicao = c.ano_eleicao || '-' || c.cd_eleicao and v.ue = c.ue
    and v.chave_cargo = lower(regexp_replace(strip_accents(c.cargo), '[^a-zA-Z0-9]', '', 'g'))

left join ultimo_turno as u on u.id_candidatura = c.id_candidatura

left join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

left join fotos as f on f.ano_eleicao = c.ano_eleicao and f.sq_candidato = c.sq_candidato
