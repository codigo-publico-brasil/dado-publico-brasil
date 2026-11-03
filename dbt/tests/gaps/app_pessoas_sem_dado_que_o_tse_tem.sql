-- Regra da ficha: se alguma candidatura do TSE da pessoa informa um atributo cadastral, a ficha (app_pessoas) o traz. Cada linha
-- é uma pessoa e um atributo que o TSE tem e a ficha não. O esperado é nenhuma.
select a.id_pessoa, 'uf_nascimento' as atributo
from {{ ref('app_pessoas') }} as a
where a.uf_nascimento is null
    and exists (select 1 from {{ ref('fct_candidaturas') }} as c where c.id_pessoa = a.id_pessoa and c.uf_nascimento is not null)

union all

select a.id_pessoa, 'escolaridade'
from {{ ref('app_pessoas') }} as a
where a.escolaridade is null
    and exists (select 1 from {{ ref('fct_candidaturas') }} as c where c.id_pessoa = a.id_pessoa and c.grau_instrucao is not null)

union all

select a.id_pessoa, 'profissoes'
from {{ ref('app_pessoas') }} as a
where a.profissoes is null
    and exists (select 1 from {{ ref('fct_candidaturas') }} as c where c.id_pessoa = a.id_pessoa and c.ocupacao is not null)

union all

select a.id_pessoa, 'estado_civil'
from {{ ref('app_pessoas') }} as a
where a.estado_civil is null
    and exists (select 1 from {{ ref('fct_candidaturas') }} as c where c.id_pessoa = a.id_pessoa and c.estado_civil is not null)

union all

select a.id_pessoa, 'foto_caminho'
from {{ ref('app_pessoas') }} as a
where a.foto_caminho is null
    and exists (select 1 from {{ ref('fct_candidaturas') }} as c where c.id_pessoa = a.id_pessoa and c.foto_caminho is not null)
