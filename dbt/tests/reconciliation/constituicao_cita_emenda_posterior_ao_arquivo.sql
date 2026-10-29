-- Erro se o texto cita uma emenda de número maior que a emenda até a qual o arquivo diz estar atualizado.
select a.parte, a.ordem, a.emenda_numero, d.atualizada_ate_emenda
from {{ ref('fct_constituicao_alteracoes') }} as a
inner join {{ ref('dim_constituicao_dispositivos') }} as d on d.parte = a.parte and d.ordem = a.ordem
where a.emenda_tipo = 'Emenda Constitucional' and a.emenda_numero > d.atualizada_ate_emenda
