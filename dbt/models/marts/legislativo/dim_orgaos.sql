-- Os órgãos onde o mandato é exercido: comissões, plenário, mesa e conselhos da Câmara e os colegiados em atividade do
-- Senado. A chave `id_orgao` é do projeto (fonte e identificador da fonte); o identificador da fonte fica ao lado para
-- auditoria. Assembleias, câmaras municipais e outros poderes entram quando tiverem fonte carregada.
select
    '{{ var("source_camara") }}' as fonte,
    '{{ var("source_camara") }}-' || id_orgao as id_orgao,
    id_orgao as id_orgao_na_fonte,
    sigla,
    apelido as nome_curto,
    nome,
    tipo_orgao as tipo,
    casa,
    situacao,
    dt_inicio,
    dt_instalacao,
    dt_fim,
    fonte_url,
    id_captura,
    cast(dt_captura as date) as dt_captura

from {{ ref('stg_camara__orgaos') }}

union all

select
    '{{ var("source_senado") }}' as fonte,
    '{{ var("source_senado") }}-' || id_colegiado as id_orgao,
    id_colegiado as id_orgao_na_fonte,
    sigla,
    cast(null as varchar) as nome_curto,
    nome,
    tipo,
    case casa_sigla when 'SF' then 'Senado Federal' when 'CN' then 'Congresso Nacional' else casa_sigla end as casa,
    'Em atividade' as situacao,
    dt_inicio,
    cast(null as date) as dt_instalacao,
    cast(null as date) as dt_fim,
    url_fonte as fonte_url,
    id_captura,
    cast(dt_captura as date) as dt_captura

from {{ ref('stg_senado__colegiados') }}
