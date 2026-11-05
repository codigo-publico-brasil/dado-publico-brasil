-- Tempo de cada nó do dbt (modelo, teste, frescor), para achar o que custa a rotina.
ALTER TABLE metadata.testes_resultados ADD COLUMN qtd_segundos DOUBLE;
COMMENT ON COLUMN metadata.testes_resultados.qtd_segundos IS 'Segundos que o dbt levou para executar o nó (execution_time do run_results.json); vazio se o dbt não informou.';
