{{ config(severity='warn') }}
-- Despesas de cota de parlamentar com nome ou identificador informado que não ligaram a uma pessoa: deputado fora do
-- cadastro carregado, ou nome do Senado sem correspondência, ambíguo (homônimo) ou sem exercício no mês. A liderança da
-- Câmara (sem deputado) não conta. Ficam sem pessoa e são medidas aqui.
select fonte, nome_parlamentar, ano, mes
from {{ ref('fct_cotas_despesas') }}
where id_pessoa is null and nome_parlamentar is not null and not (fonte = 'camara' and uf = 'NA')
