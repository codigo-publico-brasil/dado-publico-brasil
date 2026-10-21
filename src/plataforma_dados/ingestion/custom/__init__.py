"""Código próprio de uma fonte, só quando o padrão (HTTP, CSV, JSON) não basta.

Um módulo por fonte, espelhando a árvore das declarações: `custom/<poder>/<esfera>/<fonte>.py` para
`sources/<poder>/<esfera>/<fonte>.yml`. Pode definir `download(url, folder)`, `head(url)` e `records(file,
dataset)`; o que não definir segue o padrão. Exemplos de uso: SOAP, robô (RPA), pacote compactado.
"""
