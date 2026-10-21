"""Trilha de documentos e vetores (a fazer): PDF, HTML e texto de fontes oficiais.

Etapas previstas, cada uma um ativo do Dagster com linhagem até a captura no landing:
documento (landing, com hash) -> texto (parse) -> trechos (chunk) -> vetores (embed) -> índice (store).
Os trechos ficam em tabelas relacionais e são a fonte da verdade; o índice vetorial (pgvector) é derivado e
reconstruível, atrás de uma interface mínima, para poder trocar de banco. Conteúdo gerado por IA fica em
tabelas próprias, rotulado com modelo e versão. Só importa `core`.
"""
