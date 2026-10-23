{{ config(severity='warn') }}
-- Emendas cujo autor a fonte não informa (nome ou código vazio), em geral registros antigos.
select emenda_codigo, ano from {{ ref('emendas') }} where autor_nome is null or autor_codigo is null
