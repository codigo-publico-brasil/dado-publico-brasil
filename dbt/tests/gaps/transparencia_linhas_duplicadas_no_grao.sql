{{ config(severity='warn') }}
-- Despesas e contratos com mais de uma linha no grão declarado em `meta.grain` de cada staging. O `merge` por
-- `_row_hash` não apaga a linha antiga de um mês que a fonte republicou: a duplicata aparece aqui.
select 'despesas' as modelo, count(*) as linhas
from {{ ref('stg_transparencia__despesas') }}
group by dt_lancamento, cd_unidade_gestora, cd_subtitulo, cd_localizador, cd_autor_emenda, cd_elemento_despesa,
    cd_modalidade_despesa, cd_orgao_subordinado, cd_gestao, cd_unidade_orcamentaria, cd_plano_orcamentario
having count(*) > 1
union all
select 'compras', count(*)
from {{ ref('stg_transparencia__compras') }}
group by numero_contrato, cd_ug
having count(*) > 1
union all
select 'compras_itens', count(*)
from {{ ref('stg_transparencia__compras_itens') }}
group by numero_contrato, cd_ug, cd_item
having count(*) > 1
union all
select 'compras_termos_aditivos', count(*)
from {{ ref('stg_transparencia__compras_termos_aditivos') }}
group by numero_contrato, cd_ug, numero_termo_aditivo
having count(*) > 1
