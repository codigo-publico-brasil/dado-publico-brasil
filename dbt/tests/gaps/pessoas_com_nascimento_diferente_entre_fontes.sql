{{ config(severity='warn') }}
-- Pessoa cuja data de nascimento no cadastro da Câmara ou do Senado difere da de uma candidatura do TSE ligada a ela:
-- sinal de ligação errada (ou de erro de uma das fontes). O TSE usa 1º de janeiro quando só conhece o ano; essas
-- datas não entram na comparação.
select p.id_pessoa, p.dt_nascimento as dt_nascimento_oficial, c.id_candidatura, c.dt_nascimento as dt_nascimento_tse
from {{ ref('dim_pessoas') }} as p
inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.id_pessoa = p.id_pessoa and i.fonte = '{{ var("source_tse") }}' and i.id_tipo = '{{ var("id_type_tse_eleito") }}'
inner join {{ ref('stg_tse__candidaturas') }} as c on c.id_candidatura = i.id_na_fonte
where p.fonte_dt_nascimento in ('{{ var("source_camara") }}', '{{ var("source_senado") }}')
    and c.dt_nascimento is not null
    and not (month(c.dt_nascimento) = 1 and day(c.dt_nascimento) = 1)
    and c.dt_nascimento <> p.dt_nascimento
