-- A Constituição e o ADCT dispositivo a dispositivo, como a Câmara publica (texto atualizado até a emenda indicada).
-- O arquivo é uma lista de parágrafos: o tipo (título, capítulo, artigo, parágrafo, inciso, alínea, item) sai do
-- começo de cada linha e o contexto (qual artigo, parágrafo e inciso) vem da ordem. `texto` é a linha inteira, com
-- a indicação da emenda que a alterou; nada é reescrito. As linhas que não são dispositivo (cabeçalho do arquivo,
-- assinaturas) ficam marcadas e sem contexto.
with classificadas as (

    select
        parte,
        ordem,
        linha,
        emenda_do_arquivo,
        source_file_id,
        case
            when ordem = 1 then 'cabeçalho do arquivo'
            when linha = 'PREÂMBULO' then 'preâmbulo'
            when regexp_matches(linha, '^TÍTULO [IVXLC]+\b') then 'título'
            when regexp_matches(linha, '^CAPÍTULO [IVXLC]+\b') then 'capítulo'
            when regexp_matches(linha, '^SEÇÃO [IVXLC]+\b') then 'seção'
            when regexp_matches(linha, '^SUBSEÇÃO [IVXLC]+\b') then 'subseção'
            when regexp_matches(linha, '^Art\. ?\d') then 'artigo'
            when regexp_matches(linha, '^Parágrafo único') or regexp_matches(linha, '^§ ?\d') then 'parágrafo'
            when regexp_matches(linha, '^[IVXLC]+(-[A-Z])? ?[-–]') then 'inciso'
            when regexp_matches(linha, '^[a-z]\)') then 'alínea'
            when regexp_matches(linha, '^\d+\.') then 'item'
            else 'texto'
        end as tipo,
        regexp_replace(regexp_extract(linha, '^Art\. ?(\d+(?:\.\d+)*[º°]?(?:-[A-Z]+)?)', 1), '[º°]', '') as artigo_n,
        if(
            linha like 'Parágrafo único%',
            'único',
            regexp_replace(regexp_extract(linha, '^§ ?(\d+[º°]?(?:-[A-Z]+)?)', 1), '[º°]', '')
        ) as paragrafo_n,
        regexp_extract(linha, '^([IVXLC]+(?:-[A-Z])?) ?[-–]', 1) as inciso_n,
        regexp_extract(linha, '^([a-z])\)', 1) as alinea_n,
        min(ordem) filter (where regexp_matches(linha, '^Brasília, \d')) over (partition by parte) as assinaturas_desde

    from {{ ref('stg_constituicao__linhas') }}

),

marcadas as (

    select
        *,
        nullif(artigo_n, '') as artigo_marca,
        nullif(paragrafo_n, '') as paragrafo_marca,
        nullif(inciso_n, '') as inciso_marca,
        nullif(alinea_n, '') as alinea_marca,
        if(tipo = 'título', linha, null) as titulo_marca,
        if(tipo = 'capítulo', linha, null) as capitulo_marca,
        if(tipo = 'seção', linha, null) as secao_marca

    from classificadas

),

grupos as (

    select
        *,
        count(titulo_marca) over (partition by parte order by ordem) as g_titulo,
        count(artigo_marca) over (partition by parte order by ordem) as g_artigo

    from marcadas

),

grupos_2 as (

    select
        *,
        count(capitulo_marca) over (partition by parte, g_titulo order by ordem) as g_capitulo,
        count(paragrafo_marca) over (partition by parte, g_artigo order by ordem) as g_paragrafo

    from grupos

),

grupos_3 as (

    select
        *,
        count(secao_marca) over (partition by parte, g_titulo, g_capitulo order by ordem) as g_secao,
        count(inciso_marca) over (partition by parte, g_artigo, g_paragrafo order by ordem) as g_inciso

    from grupos_2

),

contexto as (

    select
        *,
        count(alinea_marca) over (partition by parte, g_artigo, g_paragrafo, g_inciso order by ordem) as g_alinea,
        max(titulo_marca) over (partition by parte, g_titulo) as titulo,
        max(capitulo_marca) over (partition by parte, g_titulo, g_capitulo) as capitulo,
        max(secao_marca) over (partition by parte, g_titulo, g_capitulo, g_secao) as secao,
        max(artigo_marca) over (partition by parte, g_artigo) as artigo,
        max(paragrafo_marca) over (partition by parte, g_artigo, g_paragrafo) as paragrafo,
        max(inciso_marca) over (partition by parte, g_artigo, g_paragrafo, g_inciso) as inciso

    from grupos_3

),

final as (

    select
        *,
        max(alinea_marca) over (partition by parte, g_artigo, g_paragrafo, g_inciso, g_alinea) as alinea,
        coalesce(ordem >= assinaturas_desde, false) as nas_assinaturas,
        coalesce(ordem >= assinaturas_desde, false)
            or tipo in ('cabeçalho do arquivo', 'preâmbulo', 'título', 'capítulo', 'seção', 'subseção') as sem_contexto

    from contexto

)

select
    f.parte,
    f.ordem,
    if(f.nas_assinaturas and f.tipo = 'texto', 'assinaturas', f.tipo) as tipo,
    case
        when f.sem_contexto or f.artigo is null then null
        else concat_ws(
            ', ',
            'Art. ' || f.artigo,
            if(f.tipo in ('parágrafo', 'inciso', 'alínea', 'item', 'texto') and f.paragrafo is not null,
                if(f.paragrafo = 'único', 'parágrafo único', '§ ' || f.paragrafo), null),
            if(f.tipo in ('inciso', 'alínea', 'item') and f.inciso is not null, f.inciso, null),
            if(f.tipo in ('alínea', 'item') and f.alinea is not null, f.alinea || ')', null),
            if(f.tipo = 'item', regexp_extract(f.linha, '^(\d+)\.', 1), null)
        )
    end as identificador,
    if(f.sem_contexto, null, f.artigo) as artigo,
    if(f.sem_contexto, null, f.paragrafo) as paragrafo,
    if(f.sem_contexto, null, f.inciso) as inciso,
    if(f.sem_contexto, null, f.alinea) as alinea,
    f.titulo,
    f.capitulo,
    f.secao,
    f.linha as texto,
    f.emenda_do_arquivo as atualizada_ate_emenda,
    'https://www2.camara.leg.br/atividade-legislativa/legislacao/constituicao1988' as fonte_url,
    cast(c.capturado_em as date) as capturado_em

from final as f

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = f.source_file_id
