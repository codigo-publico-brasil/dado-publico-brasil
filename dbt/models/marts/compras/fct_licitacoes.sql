-- Licitações do governo federal (SIASG), uma por unidade gestora, modalidade e número, como o Portal da Transparência publica.
-- Se a licitação aparece em mais de um mês, vale a captura mais recente (o teste `transparencia_linhas_duplicadas_no_grao` mede quantas).
select
    'transparencia' as fonte,
    l.id_licitacao,
    l.numero_licitacao as numero,
    l.cd_ug,
    l.ug,
    l.cd_modalidade,
    l.modalidade,
    l.numero_processo,
    l.objeto,
    l.situacao,
    l.cd_orgao_superior,
    l.orgao_superior,
    l.cd_orgao,
    l.orgao,
    l.uf,
    l.municipio,
    l.dt_resultado,
    l.dt_abertura,
    l.valor,
    l.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__licitacoes') }} as l

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = l.id_captura

qualify row_number() over (partition by l.id_licitacao order by k.dt_captura desc, l.id_captura desc) = 1
