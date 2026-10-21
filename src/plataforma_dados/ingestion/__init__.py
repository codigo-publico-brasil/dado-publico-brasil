"""Ingestão: da fonte oficial para o landing (arquivos com hash) e para o raw (dlt), com monitoramento.

Declaração das fontes em `sources/<poder>/<esfera>/<fonte>.yml`. Entrega à transformação o schema
`raw_<esfera>_<fonte>` e `metadata.captures`. Só importa `core`.
"""
