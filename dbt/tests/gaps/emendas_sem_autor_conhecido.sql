{{ config(severity='warn') }}
-- Emendas cujo autor a fonte não informa (nome ou código vazio), em geral registros antigos.
select cd_emenda, ano from {{ ref('emendas') }} where autor_nome is null or cd_autor is null
