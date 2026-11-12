-- Cota para o exercício da atividade parlamentar (CEAP): uma linha por despesa, como a Câmara publica. O CPF de fornecedor
-- pessoa física (ADR 0017) é mascarado aqui; o original fica no landing e no raw privado.
with source as (

    select * from {{ source('camara', 'cota_parlamentar') }}

),

renamed as (

    select
        _row_hash as hash_linha,
        try_cast(ide_cadastro as bigint) as id_deputado,
        proper_name(tx_nome_parlamentar) as deputado_nome,
        sg_uf as uf_sigla,
        sg_partido as partido_sigla,
        try_cast(cod_legislatura as integer) as id_legislatura,
        try_cast(num_sub_cota as integer) as cd_subcota,
        sentence_case(txt_descricao) as subcota_descricao,
        try_cast(num_especificacao_sub_cota as integer) as cd_especificacao,
        sentence_case(txt_descricao_especificacao) as especificacao_descricao,
        clean_text(txt_fornecedor) as fornecedor_nome,
        mascarar_dado_pessoal(clean_text(txt_cnpjcpf), 'favorecido') as fornecedor_documento,
        length(regexp_replace(txt_cnpjcpf, '[^0-9]', '', 'g')) = 11 as fl_fornecedor_pessoa_fisica,
        clean_text(txt_numero) as numero_documento,
        try_cast(ind_tipo_documento as integer) as cd_tipo_documento,
        cast(try_cast(dat_emissao as timestamp) as date) as dt_emissao,
        try_cast(vlr_documento as decimal(18, 2)) as valor_documento,
        try_cast(vlr_glosa as decimal(18, 2)) as valor_glosa,
        try_cast(vlr_liquido as decimal(18, 2)) as valor_liquido,
        try_cast(num_mes as integer) as mes,
        try_cast(num_ano as integer) as ano,
        try_cast(num_parcela as integer) as numero_parcela,
        clean_text(txt_trecho) as trecho,
        try_cast(num_lote as bigint) as id_lote,
        try_cast(num_ressarcimento as bigint) as id_ressarcimento,
        cast(try_cast(dat_pagamento_restituicao as timestamp) as date) as dt_pagamento_restituicao,
        try_cast(vlr_restituicao as decimal(18, 2)) as valor_restituicao,
        try_cast(ide_documento as bigint) as id_documento,
        url_documento,
        _source_file_id as id_captura

    from source

)

{{ colunas_auditoria('renamed') }}
