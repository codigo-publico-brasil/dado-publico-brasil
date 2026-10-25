{{ config(severity='warn') }}
-- Fila de revisão: eleito ao Congresso que a regra automática não ligou a uma pessoa, mas que tem alguém com a mesma data
-- de nascimento na Câmara ou no Senado (nome civil escrito de outro jeito, por exemplo). Data de nascimento igual não prova
-- que é a mesma pessoa: uma pessoa confere e, se for, aprova o vínculo em `vinculos_aprovados`, com a evidência. Enquanto isso
-- o eleito aparece como novato, nunca como reeleito.
select
    e.id_candidatura,
    e.nome,
    p.fonte as fonte_possivel,
    p.id_na_fonte as id_na_fonte_possivel

from {{ ref('eleitos') }} as e

inner join {{ ref('stg_tse__candidaturas') }} as c
    on c.id_candidatura = e.id_candidatura and c.turno = e.turno

inner join {{ ref('int_pessoas_vinculo') }} as p on p.dt_nascimento = c.dt_nascimento

where e.id_pessoa is null and e.cargo in ('Deputado federal', 'Senador')
