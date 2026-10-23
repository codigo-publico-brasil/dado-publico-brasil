{{ config(severity='warn') }}
-- Emendas que o texto da Câmara cita como alteração da Constituição (parte permanente) e o Senado não declara como
-- alteração permanente dela. O contrário é esperado (o texto só cita a última emenda de cada trecho).
select distinct a.emenda_numero
from {{ ref('constituicao_alteracoes') }} as a
where a.parte = 'Constituição'
    and a.emenda_tipo = 'Emenda Constitucional'
    and a.tipo_alteracao in ('redação dada', 'incluído', 'revogado', 'suprimido', 'renumerado')
    and a.emenda_numero is not null
    and not exists (
        select 1
        from {{ ref('normas_relacoes') }} as r
        where r.norma_id = 579494
            and r.tipo_relacao like '%Alteração Permanente%'
            and r.norma_posterior_nome like 'Emenda Constitucional n%'
            and try_cast(regexp_extract(r.norma_posterior_nome, 'Emenda Constitucional nº ?(\d+)', 1) as integer)
                = a.emenda_numero
    )
