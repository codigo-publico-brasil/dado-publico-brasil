-- Cada indicação de emenda que o texto da Constituição traz entre parênteses, por dispositivo ("Redação dada pela
-- Emenda Constitucional nº 45, de 2004"). Uma linha por dispositivo e emenda citada. `tipo_alteracao` sai das
-- palavras da própria nota; `vide` é só referência. O número é o que vem logo depois de "Emenda Constitucional nº"
-- (ou das listas "nºs 20 e 41"); o ano só é preenchido quando a nota cita uma emenda.
with notas as (

    select
        parte,
        ordem,
        identificador,
        unnest(regexp_extract_all(texto, '\(([^()]*Emenda[^()]*)(?:\)|$)', 1)) as nota

    from {{ ref('constituicao_dispositivos') }}

    where texto like '%Emenda%'

),

classificadas as (

    select
        *,
        case
            when lower(nota) like '%revogad%' then 'revogado'
            when lower(nota) like '%suprimid%' then 'suprimido'
            when lower(nota) like '%acrescid%' or lower(nota) like '%incluíd%' or lower(nota) like '%acrescentad%'
                then 'incluído'
            when lower(nota) like '%redação dada%' or lower(nota) like '%nova redação%' then 'redação dada'
            when lower(nota) like '%renumerad%' or lower(nota) like '%transformad%' then 'renumerado'
            when lower(nota) like 'vide%' then 'vide'
            else 'outra'
        end as tipo_alteracao,
        if(nota like '%de Revisão%', 'Emenda Constitucional de Revisão', 'Emenda Constitucional') as emenda_tipo,
        regexp_extract_all(
            regexp_extract(
                nota,
                'Emendas? Constitucion(?:al|ais)(?: de Revisão)? n[º°os]+ ?(\d{1,3}(?:(?:, | e )\d{1,3}\b)*)',
                1
            ),
            '\d+'
        ) as numeros,
        try_cast(regexp_extract(nota, '\b(\d{4})\b', 1) as integer) as ano_citado

    from notas

)

select
    parte,
    ordem,
    identificador,
    tipo_alteracao,
    emenda_tipo,
    try_cast(unnest(if(len(numeros) = 0, [cast(null as varchar)], numeros)) as integer) as emenda_numero,
    if(len(numeros) = 1, ano_citado, null) as emenda_ano,
    nota

from classificadas
