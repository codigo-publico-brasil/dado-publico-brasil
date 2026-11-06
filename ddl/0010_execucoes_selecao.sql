-- Reconstrução seletiva do dbt (ADR 0047): o que cada execução guarda para a seguinte decidir o que pular.
ALTER TABLE metadata.execucoes ADD COLUMN fl_completa BOOLEAN;
ALTER TABLE metadata.execucoes ADD COLUMN impressao_antes VARCHAR;
ALTER TABLE metadata.execucoes ADD COLUMN impressao_depois VARCHAR;
COMMENT ON COLUMN metadata.execucoes.fl_completa IS 'Verdadeiro na execução de uma fase do dbt que reconstruiu todos os modelos da fase (não só os que mudaram) e deixou resultado de todos; base de "mesmo código e domingo" da reconstrução completa. Vazio nas demais etapas.';
COMMENT ON COLUMN metadata.execucoes.impressao_antes IS 'Etapa identity: impressão digital (contagem e soma do hash das linhas) de pessoas, pessoas_identificadores e pessoas_fusoes antes de a execução mexer nelas; vazio nas demais etapas.';
COMMENT ON COLUMN metadata.execucoes.impressao_depois IS 'Etapa identity: a mesma impressão digital depois da execução; diferente da anterior = a identidade mudou e os modelos que a leem precisam ser refeitos; vazio nas demais etapas.';
