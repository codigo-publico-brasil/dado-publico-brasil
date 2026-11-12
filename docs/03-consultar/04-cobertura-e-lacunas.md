# Cobertura e lacunas

Para quem quer saber o que as fontes oficiais deixaram de entregar ao projeto e desde quando. Gerado de `marts/fontes/fct_fontes_ocorrencias`, `marts/fontes/agg_fontes_capturas` e `metadata/testes_resultados` (`dado-publico gaps`). Não edite à mão: o método é o SQL desses modelos e a descrição das colunas ([ADR 0054](../05-decisoes/0054-fato-agregado-e-avaliacao.md)). É medição da publicação das fontes, sem nota nem ranking; uma falha de rede do projeto pode aparecer como indisponibilidade da fonte (veja a descrição da tabela).

Ainda não gerado neste commit: rode `uv run dado-publico gaps` depois de `transform`, com o warehouse atual.
