# Documentação

Para quem chega ao projeto: onde cada coisa mora em `docs/` e em que ordem ler. As pastas têm um propósito cada (explicar, fazer, consultar) e os arquivos levam `NN-` pela ordem de leitura sugerida.

| Pasta | Propósito | Quando ler |
| --- | --- | --- |
| [`01-entender/`](01-entender/) | **Explicação:** o que o projeto é, como é construído e por quê | primeiro, na ordem dos números |
| [`02-fazer/`](02-fazer/) | **Como fazer:** passo a passo para rodar, operar, auditar e acrescentar fonte | quando for pôr a mão na massa |
| [`03-consultar/`](03-consultar/) | **Referência:** catálogo de tabelas, convenção de nomes, fontes, lacunas | quando precisar de um fato exato |
| [`04-dominio/`](04-dominio/) | Material didático sobre as instituições (Câmara, Senado, TSE...) e as regras por trás dos campos | para entender os dados |
| [`05-decisoes/`](05-decisoes/) | ADRs: decisões de arquitetura aceitas, uma por arquivo (`0001`...) | para saber por que algo é assim |
| [`99-historico/`](99-historico/) | Planos e propostas antigos, guardados só como registro | normalmente, nunca |

## Ordem de leitura

1. [`01-entender/`](01-entender/), na ordem: visão geral, arquitetura, camadas, ferramentas.
2. [`01-entender/05-identidade-de-pessoas.md`](01-entender/05-identidade-de-pessoas.md) e [`06-governanca.md`](01-entender/06-governanca.md).
3. [`02-fazer/01-rodar-localmente.md`](02-fazer/01-rodar-localmente.md).
4. [`02-fazer/03-especificacao-de-fonte.md`](02-fazer/03-especificacao-de-fonte.md), [`04-operar-e-publicar.md`](02-fazer/04-operar-e-publicar.md) e [`05-auditar.md`](02-fazer/05-auditar.md).
5. [`03-consultar/`](03-consultar/): conforme a necessidade.

O número que falta (`02-fazer/02`, tutorial de nova fonte) ainda será escrito.

## Regras

1. **Um assunto, um lugar.** Antes de criar um arquivo, procure se o assunto já tem um; os outros apenas linkam.
2. **Todo documento começa dizendo para quem é e o que responde.**
3. **Uma decisão aceita não é editada:** vira um ADR novo que a substitui.
4. **Itens e pendências ficam em issues** do repositório, não em arquivos `.md`.
5. **O catálogo ([`03-consultar/01-catalogo.md`](03-consultar/01-catalogo.md)) é gerado** (`uv run dado-publico catalog`); um teste falha se estiver desatualizado.
6. **Quem muda comportamento atualiza o documento no mesmo PR.**
7. Documentos de produto da aplicação ficam no repositório [quem-decidiu](https://github.com/codigo-publico-brasil/quem-decidiu).
