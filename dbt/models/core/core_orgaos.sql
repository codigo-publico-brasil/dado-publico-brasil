-- Os órgãos onde o mandato é exercido: comissões, plenário, mesa e conselhos da Câmara. A chave `id_orgao` é do projeto
-- (fonte e identificador da fonte); o identificador da fonte fica ao lado para auditoria. Senado, assembleias e câmaras
-- municipais ainda não têm fonte carregada; entram aqui quando tiverem.
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
    id_captura

from {{ ref('stg_camara__orgaos') }}
