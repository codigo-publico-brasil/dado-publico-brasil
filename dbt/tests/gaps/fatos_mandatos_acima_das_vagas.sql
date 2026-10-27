{{ config(severity='warn') }}
-- Disputas com mais mandatos eleitos do que vagas no arquivo de vagas do TSE (sobreposição impossível na mesma vaga).
-- Hoje: prefeitos de 2000 com dois eleitos na mesma unidade, suplentes de senador de 2014 a 2022 (o arquivo de vagas
-- traz 1 vaga e a eleição renovou 2/3 do Senado) e vereadores; a causa está na fonte, não é corrigida aqui.
select m.id_disputa, d.qtd_vagas, count(*) as qtd_mandatos
from {{ ref('fatos_mandatos') }} as m
inner join {{ ref('disputas') }} as d on d.id_disputa = m.id_disputa
group by m.id_disputa, d.qtd_vagas
having count(*) > d.qtd_vagas
