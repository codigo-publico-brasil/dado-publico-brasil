-- Dispositivos vetados de cada veto, com o texto vetado, a razão do veto e a situação (mantido, rejeitado...).
select
    try_cast(codigo as bigint) as id_dispositivo,
    try_cast(_item as bigint) as id_materia_veto,
    identificador,
    descricao,
    conteudo as texto_vetado,
    razao_veto,
    situacao,
    possui_votos = 'Sim' as fl_possui_votos,
    tipo_votacao,
    try_cast(data_sessao as date) as dt_sessao,
    _source_file_id as id_captura

from {{ source('senado', 'vetos_dispositivos') }}
