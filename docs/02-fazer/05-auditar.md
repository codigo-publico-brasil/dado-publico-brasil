# Auditoria e qualidade: como provar o que o dado diz

Para quem precisa **confiar** nos dados ou **conferir** de onde veio cada um. Responde: o que a plataforma guarda para poder provar a origem, como conferir que nada mudou e como saber o que falta. As regras estão em [governança](../01-entender/06-governanca.md); o desenho das camadas, em [camadas](../01-entender/03-camadas.md).

## O rastro de um dado, da tabela até a resposta da fonte

```text
mart (fct_proposicoes_tramitacoes)
  -> staging e raw: cada linha do raw leva `_source_file_id`
     -> metadata.capturas: URL, hash, tamanho, data, caminho do arquivo no landing, execução que trouxe
        -> arquivo do landing (imutável, com o hash no nome)
           -> nos datasets por item: o lote guarda a resposta de cada item byte a byte
              -> metadata.capturas_itens: item, URL, status HTTP, hash do corpo, data, versão
```

Toda execução (`metadata.execucoes`) registra a versão do código (commit), linhas lidas e gravadas e o resultado; o dbt grava cada modelo e teste em `metadata.testes_resultados`.

## O que se confere, e com qual comando

| Pergunta | Como responder |
| --- | --- |
| O arquivo guardado é o que a fonte entregou? | `uv run dado-publico verify`: recalcula o hash de todo arquivo do landing e compara com `metadata.capturas` |
| Cada resposta de um dataset por item continua igual? | o mesmo `verify` confere o hash de cada resposta dentro dos lotes e o índice `metadata.capturas_itens` |
| Quanto já foi buscado e quanto falta? | `uv run dado-publico coverage`: itens esperados, obtidos, inexistentes (404), com falha e faltantes, por dataset |
| A fonte respondeu, mudou de colunas, encolheu? | `metadata.fontes_verificacoes` (`availability`, `schema`, `volume`, `coverage`) |
| O dado está fresco? | `dt_verificacao` em `metadata.capturas` (última verificação da fonte); o atraso por dataset aparece no Dagster e em `dado-publico observe` |
| Alguma linha se perdeu entre as camadas? | testes de reconciliação do dbt (severidade erro), por exemplo `votos_perdidos_do_staging_aos_marts` |
| O raw tem linha a mais ou a menos que a captura vigente (ano duplicado)? | `carga_do_raw_diferente_da_captura`: nos datasets `replace_partition` (marcados com `meta.escrita` no YAML de sources do dbt), compara as linhas do raw por partição com as `carregadas` da carga em `metadata.fontes_verificacoes` |
| Quais lacunas conhecidas existem e de que tamanho? | testes `warn` do dbt (a contagem de linhas que falham mede a lacuna) e [cobertura e lacunas](../03-consultar/04-cobertura-e-lacunas.md) |

`verify` sai com erro se algo não confere, o que serve para agendar. Os testes automatizados cobrem o caso adulterado: um arquivo ou uma resposta alterada depois da captura é apontada.

## Regras que tornam isso possível

1. **O landing nunca é editado nem apagado**: o arquivo recebe o hash no nome, e uma mudança na fonte gera um segundo arquivo.
2. **Nada é completado por suposição**: faltou, fica vazio, e o teste mede a lacuna.
3. **A resposta é guardada antes de ser interpretada**: o corpo vai ao landing byte a byte; o raw, o staging e os marts se refazem a partir dele.
4. **Falha não some**: erro de fonte, item inexistente e resposta incompleta ficam registrados com o status; só os erros de disponibilidade e de colunas aparecem como verificação.
5. **Reprodutível**: raw, staging, intermediate e marts se refazem do landing (`load --rebuild`, `transform`); só `identity` (a chave própria) não, e por isso é criada por migração.

## O que ainda não existe

- Amostragem contra as páginas oficiais (cada número conferido à mão) e relatório periódico de `verify`.
- Alerta (e-mail ou mensagem) quando `verify`, `schema` ou `volume` falham; hoje o registro é em tabela.
- Exibir a linhagem no aplicativo que consome os dados.

## Datasets por item e auditoria

Tramitação e situação só existem por item (uma chamada por proposição). Um dataset `load: foreach` busca, em lotes e a uma taxa educada, os itens que faltam ou mudaram, começando pelos mais recentes; roda só com `--foreach N` ou `--foreach all`. Cada lote guarda a resposta de cada item byte a byte, e dois comandos auditam: `dado-publico verify` (hashes do landing e do índice `metadata.capturas_itens`) e `dado-publico coverage` (itens esperados, obtidos, inexistentes, com falha e faltantes). Detalhes no [ADR 0012](../05-decisoes/0012-dataset-por-item-lotes-com-envelope.md). Um dataset por item pode listar os itens de outro dataset por item (os dispositivos vetados saem dos vetos, e os votos saem dos dispositivos): na execução completa o raw é carregado depois de cada um, então a cadeia roda numa vez; pelos comandos `extract` e `load` em separado, uma etapa por rodada.


## Monitoramento das fontes

Cada captura grava em `metadata.fontes_verificacoes` (status `ok`, `warn` ou `error`): `availability` (a fonte respondeu?), `schema` (coluna do contrato ausente é erro; coluna nova ou removida é aviso) e `volume` (menos de 80% das linhas da carga anterior é aviso). O frescor é medido pela última verificação (`max_age_days` e o sensor `verificar_atrasos`). Nada interrompe o pipeline; a execução devolve `source_errors`. Consulta:

```bash
uv run dado-publico query --sql "SELECT * FROM metadata.fontes_verificacoes WHERE resultado <> 'ok' ORDER BY id_verificacao DESC LIMIT 20"
```

O `detalhe` é o texto para gente; o que o código e os testes usam tem coluna própria (ADR 0053): `cd_status_http` (código da resposta), `tipo_ocorrencia` (`nao_encontrado`, `nao_publicado`, `erro_http`, `falha_de_rede`, `bloqueio`, `html_no_lugar`, `tamanho_divergente`, `zip_invalido`), `qtd_bytes_esperados` e `qtd_bytes_recebidos` (integridade e disponibilidade) e `qtd_linhas` (carga, volume e linhas removidas). Consulta por tipo, sem buscar no texto:

```bash
uv run dado-publico query --sql "SELECT fonte, dataset, particao, cd_status_http FROM metadata.fontes_verificacoes WHERE tipo_ocorrencia = 'nao_encontrado'"
```

As linhas anteriores à migração 0012 foram preenchidas por extração do `detalhe`; o que não casou ficou vazio.
