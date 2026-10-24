-- Quem recebeu o dinheiro de cada emenda, por mês, como a fonte publica. Inclui pessoa física, com o CPF mascarado.
select
    nullif(nullif(c_digo_da_emenda, 'Sem informação'), 'S/I') as emenda_codigo,
    nullif(nullif(c_digo_do_autor_da_emenda, 'Sem informação'), 'S/I') as autor_codigo,
    proper_name(nullif(nome_do_autor_da_emenda, 'Sem informação')) as autor_nome,
    nullif(nullif(n_mero_da_emenda, 'Sem informação'), 'S/I') as numero,
    tipo_de_emenda as tipo,
    try_cast(substr(ano_m_s, 1, 4) as integer) as ano,
    try_cast(substr(ano_m_s, 5, 2) as integer) as mes,
    c_digo_do_favorecido as favorecido_codigo,
    favorecido,
    natureza_jur_dica as natureza_juridica,
    tipo_favorecido,
    uf_favorecido as uf,
    munic_pio_favorecido as municipio,
    try_cast(replace(valor_recebido, ',', '.') as decimal(18, 2)) as valor,
    _source_file_id as source_file_id

from {{ source('transparencia', 'emendas_favorecidos') }}
