with source as (

    select * from {{ source('senado', 'votacoes') }}

),

renamed as (

    select
        try_cast(codigo_sessao_votacao as bigint) as id_votacao,
        try_cast(data_sessao as date) as dt_votacao,
        votacao_secreta = 'S' as fl_secreta,
        resultado_votacao as resultado,
        try_cast(total_votos_sim as integer) as votos_sim,
        try_cast(total_votos_nao as integer) as votos_nao,
        try_cast(total_votos_abstencao as integer) as votos_abstencao,
        mascarar_dado_pessoal(descricao_votacao, 'cpf') as descricao,
        informe_legislativo_sigla_colegiado as orgao_sigla,
        try_cast(codigo_materia as bigint) as id_materia,
        identificacao as materia_sigla,
        try_cast(data_apresentacao as date) as dt_materia_apresentacao,
        mascarar_dado_pessoal(regexp_replace(ementa, '^\s+|\s+$', '', 'g'), 'cpf') as materia_ementa,
        try_cast(codigo_sessao as bigint) as id_sessao,
        sigla_tipo_sessao as sessao_tipo_sigla,
        try_cast(id_processo as bigint) as id_processo,
        sigla as materia_sigla_tipo,
        try_cast(numero as integer) as materia_numero,
        try_cast(ano as integer) as materia_ano,
        informe_legislativo_nome_colegiado as orgao_nome,
        _source_file_id as id_captura

    from source

)

{{ colunas_auditoria('renamed') }}
