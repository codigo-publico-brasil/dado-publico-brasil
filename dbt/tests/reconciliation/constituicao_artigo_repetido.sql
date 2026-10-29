-- Erro se o mesmo número de artigo aparece duas vezes na mesma parte (sinal de que a leitura do arquivo se perdeu).
select parte, artigo
from {{ ref('dim_constituicao_dispositivos') }}
where tipo = 'artigo'
group by parte, artigo
having count(*) > 1
