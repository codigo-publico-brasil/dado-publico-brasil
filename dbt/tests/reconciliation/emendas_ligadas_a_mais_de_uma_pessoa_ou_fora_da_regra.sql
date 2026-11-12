-- ADR 0056: uma emenda só liga a uma pessoa; só a individual liga; código de autor com mais de um nome na fonte não
-- liga. Qualquer linha aqui é vínculo que a regra não permite.
select cd_autor, ano
from {{ ref('fct_emendas') }}
where id_pessoa is not null
group by cd_autor, ano
having count(distinct id_pessoa) > 1
    or bool_or(tipo not like 'Emenda Individual%')
    or cd_autor in (
        select cd_autor from {{ ref('fct_emendas') }}
        where autor_nome is not null group by cd_autor having count(distinct lower(strip_accents(autor_nome))) > 1
    )
