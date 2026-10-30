
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

turnos_votados as (

    -- o turno também pode vir só da votação (em 2006 o arquivo de candidaturas não tem o 2º turno de presidente)
    select id_candidatura, max(turno) as ultimo_turno_votado from {{ ref('fct_resultados') }} group by id_candidatura

),

ultimo_turno as (

    -- o mais votado do último turno com votos, para a disputa de uma vaga (derivado dos votos, ver `resultados`)
    select id_candidatura, fl_mais_votado_no_turno

    from {{ ref('fct_resultados') }}

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
        id_candidatura, ano_eleicao, cd_eleicao, ue, cd_cargo, sq_candidato, numero, numero_partido, nome, nome_urna, nome_social, genero,
        grau_instrucao, estado_civil, ocupacao, uf_nascimento, partido_sigla, partido_nome, federacao_sigla, coligacao_nome

    from {{ ref('stg_tse__candidaturas') }}

    order by id_candidatura, turno

)

select
    '{{ var("source_tse") }}' as fonte,
    c.id_candidatura,
    v.id_disputa,
    c.sq_candidato,
    c.numero,
    c.numero_partido,
    c.nome,
    c.nome_urna,
    c.nome_social,
    c.genero,
    c.grau_instrucao,
    c.estado_civil,
    c.ocupacao,
    c.uf_nascimento,
    ps.id_partido,
    c.partido_sigla as partido,
    c.partido_nome,
    c.federacao_sigla as federacao,
    c.coligacao_nome as coligacao,
    t.situacao_candidatura,
    greatest(t.qtd_turnos, coalesce(tv.ultimo_turno_votado, 0)) as qtd_turnos,
    t.resultado,
    t.fl_eleito,
    u.fl_mais_votado_no_turno as fl_mais_votado_no_ultimo_turno,
    p.id_pessoa_tse,
    coalesce(pe.id_pessoa, pc.id_pessoa) as id_pessoa,
    f.arquivo as foto_arquivo,
    if(
        f.arquivo is not null,
        c.ano_eleicao || '/' || f.pacote_uf || '/' || c.sq_candidato || '.' || regexp_extract(f.arquivo, '[.](jpe?g|png)$', 1),
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

left join {{ ref('dim_cargos') }} as k on k.cd_cargo_tse = c.cd_cargo

left join {{ ref('dim_disputas') }} as v
    on v.id_eleicao = c.ano_eleicao || '-' || c.cd_eleicao and v.ue = c.ue and v.id_cargo = k.id_cargo

left join {{ ref('partidos_siglas') }} as ps
    on ps.sigla_na_fonte = c.partido_sigla
    and ps.nr_partido = try_cast(c.numero_partido as integer)
    and try_cast(c.ano_eleicao as integer) between ps.ano_inicio and ps.ano_fim

left join turnos_votados as tv on tv.id_candidatura = c.id_candidatura

left join ultimo_turno as u on u.id_candidatura = c.id_candidatura

left join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

left join {{ ref('stg_identity__pessoa_identificadores') }} as pe
    on pe.fonte = '{{ var("source_tse") }}' and pe.id_tipo = '{{ var("id_type_tse_eleito") }}' and pe.id_na_fonte = c.id_candidatura

-- candidatura de quem já era deputado ou senador (ligada pelo nome civil ou de urna e o nascimento), mesmo sem ter sido eleito
left join {{ ref('stg_identity__pessoa_identificadores') }} as pc
    on pc.fonte = '{{ var("source_tse") }}' and pc.id_tipo = '{{ var("id_type_tse") }}' and pc.id_na_fonte = c.id_candidatura

left join fotos as f on f.ano_eleicao = c.ano_eleicao and f.sq_candidato = c.sq_candidato
