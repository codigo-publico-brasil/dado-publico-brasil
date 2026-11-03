-- CPF completo não pode sair em texto livre: o staging o mascara (macro mascarar_dado_pessoal); o original fica no landing.
-- Padrões: nnn.nnn.nnn-nn (com ou sem rótulo; número com mais grupos pontuados, como CNPJ mal digitado, não conta) e "CPF" + 11 dígitos; favorecido ainda confere 11 dígitos soltos.
with textos as (

    select 'stg_tse__bens.descricao' as coluna, descricao as texto from {{ ref('stg_tse__bens') }}
    union all select 'stg_tse__despesas_candidatos.descricao', descricao from {{ ref('stg_tse__despesas_candidatos') }}
    union all select 'stg_tse__receitas_candidatos.descricao', descricao from {{ ref('stg_tse__receitas_candidatos') }}
    union all select 'fct_candidaturas_bens.descricao', descricao from {{ ref('fct_candidaturas_bens') }}
    union all select 'stg_camara__proposicoes.ementa', ementa from {{ ref('stg_camara__proposicoes') }}
    union all select 'fct_proposicoes.ementa', ementa from {{ ref('fct_proposicoes') }}
    union all select 'fct_proposicoes.ementa_oficial', ementa_oficial from {{ ref('fct_proposicoes') }}
    union all select 'stg_senado__votacoes.materia_ementa', materia_ementa from {{ ref('stg_senado__votacoes') }}
    union all select 'stg_camara__votacoes.descricao', descricao from {{ ref('stg_camara__votacoes') }}
    union all select 'stg_senado__votacoes.descricao', descricao from {{ ref('stg_senado__votacoes') }}
    union all select 'stg_transparencia__emendas_favorecidos.favorecido', favorecido from {{ ref('stg_transparencia__emendas_favorecidos') }}
    union all select 'fct_emendas_favorecidos.favorecido', favorecido from {{ ref('fct_emendas_favorecidos') }}

)

select coluna, texto from textos
where regexp_matches(texto, '(^|[^0-9.])\d{3}\.\d{3}\.\d{3}-\d{2}')
    or regexp_matches(texto, 'CPF\D{0,8}\d{11}(\D|$)', 'i')

union all
select 'stg_transparencia__emendas_favorecidos', favorecido from {{ ref('stg_transparencia__emendas_favorecidos') }}
where regexp_matches(favorecido, '(^|[^0-9])[0-9]{11}([^0-9]|$)') or regexp_matches(cd_favorecido, '^[0-9]{11}$')
union all
select 'fct_emendas_favorecidos', favorecido from {{ ref('fct_emendas_favorecidos') }}
where regexp_matches(favorecido, '(^|[^0-9])[0-9]{11}([^0-9]|$)') or regexp_matches(cd_favorecido, '^[0-9]{11}$')
