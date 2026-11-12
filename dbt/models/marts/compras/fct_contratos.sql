-- Contratos do governo federal, um por unidade gestora e número do contrato, como o Portal da Transparência publica. Contratado
-- pessoa física (CPF mascarado) fica marcado em `fl_contem_dado_pessoal`. Se o contrato aparece em mais de um mês, vale a
-- captura mais recente (o teste `transparencia_linhas_duplicadas_no_grao` mede quantas).
select
    'transparencia' as fonte,
    c.id_contrato,
    c.numero_contrato as numero,
    c.cd_ug,
    c.ug,
    c.cd_orgao_superior,
    c.orgao_superior,
    c.cd_orgao,
    c.orgao,
    c.objeto,
    c.fundamento_legal,
    c.modalidade_compra as modalidade,
    c.situacao,
    c.dt_assinatura,
    c.dt_publicacao_dou,
    c.dt_inicio_vigencia,
    c.dt_fim_vigencia,
    c.cd_contratado,
    c.contratado,
    coalesce(c.cd_contratado like '%*%', false) as fl_contem_dado_pessoal,
    c.valor_inicial,
    c.valor_final,
    c.id_licitacao,
    c.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__compras') }} as c

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = c.id_captura

qualify row_number() over (partition by c.id_contrato order by k.dt_captura desc, c.id_captura desc) = 1
