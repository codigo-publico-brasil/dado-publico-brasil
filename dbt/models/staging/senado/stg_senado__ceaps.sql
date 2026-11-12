-- Cota para o exercício da atividade parlamentar dos senadores (CEAPS): uma linha por despesa reembolsada, como o Senado
-- publica. A fonte traz só o nome do senador (sem código). CPF de fornecedor pessoa física e no texto de detalhamento é
-- mascarado (ADR 0017); o original fica no landing e no raw privado.
with source as (

    select * from {{ source('senado', 'ceaps') }}

),

renamed as (

    select
        _row_hash as hash_linha,
        try_cast(ano as integer) as ano,
        try_cast(mes as integer) as mes,
        proper_name(senador) as senador_nome,
        sentence_case(tipo_despesa) as tipo_despesa,
        clean_text(fornecedor) as fornecedor_nome,
        mascarar_dado_pessoal(clean_text(cnpj_cpf), 'favorecido') as fornecedor_documento,
        length(regexp_replace(cnpj_cpf, '[^0-9]', '', 'g')) = 11 as fl_fornecedor_pessoa_fisica,
        clean_text(documento) as numero_documento,
        cast(try_strptime(data, '%d/%m/%Y') as date) as dt_emissao,
        mascarar_dado_pessoal(clean_text(detalhamento), 'favorecido') as detalhamento,
        try_cast(replace(valor_reembolsado, ',', '.') as decimal(18, 2)) as valor_reembolsado,
        try_cast(cod_documento as bigint) as id_documento,
        _source_file_id as id_captura

    from source

)

{{ colunas_auditoria('renamed') }}
