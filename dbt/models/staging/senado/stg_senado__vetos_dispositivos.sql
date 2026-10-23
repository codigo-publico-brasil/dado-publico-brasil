-- Dispositivos vetados de cada veto, com o texto vetado, a razão do veto e a situação (mantido, rejeitado...).
select
    try_cast(codigo as bigint) as dispositivo_id,
    try_cast(_item as bigint) as materia_veto_id,
    identificador,
    descricao,
    conteudo as texto_vetado,
    razao_veto,
    situacao,
    possui_votos = 'Sim' as possui_votos,
    tipo_votacao,
    try_cast(data_sessao as date) as sessao_em,
    _source_file_id as source_file_id

from {{ source('senado', 'vetos_dispositivos') }}
