{{ config(severity='warn') }}
-- A padronização de caixa deveria ter pego todos os nomes com mais de uma palavra.
select id_pessoa from {{ ref('pessoas') }}
where nome = upper(nome) and nome <> lower(nome) and nome like '% %'
