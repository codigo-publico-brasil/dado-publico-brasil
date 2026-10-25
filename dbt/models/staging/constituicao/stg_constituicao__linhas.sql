-- Uma linha por parágrafo de texto do arquivo da Constituição e do ADCT, como publicado. A classificação em
-- título, artigo, parágrafo, inciso e alínea é do mart `constituicao_dispositivos`.
select
    'Constituição' as parte,
    try_cast(ordem as integer) as ordem,
    linha,
    try_cast(emenda_do_arquivo as integer) as emenda_do_arquivo,
    _source_file_id as id_captura

from {{ source('constituicao', 'constituicao') }}

union all

select
    'ADCT',
    try_cast(ordem as integer),
    linha,
    try_cast(emenda_do_arquivo as integer),
    _source_file_id

from {{ source('constituicao', 'adct') }}
