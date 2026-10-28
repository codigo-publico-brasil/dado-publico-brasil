-- Uma linha por votação e proposição, com o resultado e os totais. Só leitura de marts.votacoes e fatos.votacoes_proposicoes.
select
    v.fonte,
    v.id_votacao,
    v.dt_votacao,
    vp.papel,
    pr.sigla as proposicao,
    pr.ementa,
    pr.fonte_url as url_proposicao,
    v.descricao,
    v.aprovada,
    v.votos_sim,
    v.votos_nao,
    v.votos_outros

from {{ ref('votacoes') }} as v

inner join {{ ref('fatos_votacoes_proposicoes') }} as vp on vp.fonte = v.fonte and vp.id_votacao = v.id_votacao

left join {{ ref('proposicoes') }} as pr on pr.fonte = vp.fonte and pr.id_proposicao = vp.id_proposicao
