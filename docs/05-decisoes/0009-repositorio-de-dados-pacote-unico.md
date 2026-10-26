# ADR 0009: Repositório oficial da camada de dados, em um só pacote Python

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Substitui em parte:** [ADR 0008](0008-motores-separados-e-organizacao-por-poder-e-esfera.md) (os cinco pacotes viram subpacotes de um só). Mantém dele: poder/esfera/fonte, captura por adaptador, monitoramento das fontes, a separação entre os motores.

## Contexto

O projeto muda de propósito: este repositório passa a ser a **plataforma de dados**, executada em infraestrutura própria (pipelines, banco de consumo, trilha de documentos com banco vetorial e IA). O Quem Decidiu vira uma aplicação, em outro repositório, e outras aplicações poderão usar os mesmos dados. Com o app fora, cinco `pyproject.toml` em um workspace deixam de compensar. O fundador pediu a estrutura de menos código e menos arquivos (menos manutenção e menos tokens para agentes).

## Decisão

1. **Um só pacote Python, `plataforma_dados`**, com os subpacotes `core`, `ingestion`, `transformation`, `orchestration` (e, depois, `documents`). Um só `pyproject.toml`, com **extras** por motor (`ingestion`, `transformation`, `orchestration`): imagens de implantação podem instalar só o necessário; `uv sync --all-extras` instala tudo.
2. **A fronteira entre os motores continua** e é testada: `ingestion` e `transformation` só importam `core`; só `orchestration` conhece os dois. Separar em distribuições, se um dia for preciso, continua barato.
3. **O que é declaração fica fora do pacote, na raiz:** `sources/` (fontes), `dbt/` (projeto dbt, na convenção de ter pasta própria) e `ddl/` (migrações SQL). Elas são localizadas a partir da raiz do repositório, o que serve a contêineres que copiam o repositório.
4. **Configuração só por variáveis de ambiente** (`PLATAFORMA_STORAGE_ROOT`, `PLATAFORMA_WAREHOUSE`), sem arquivo de configuração: o padrão está no código, e a infraestrutura (a decidir) injeta o resto. Sem código específico de nuvem.
5. **Linha de comando `plataforma`** (`uv run plataforma run ...`).
6. **Regras de dados no repositório; regras de apresentação nas aplicações.** Ficam aqui: fonte, URL e data em todo dado, landing imutável, nada inventado, sem documento pessoal, sem métrica avaliativa derivada, conteúdo de IA rotulado e em tabelas próprias.
7. **A aplicação sai.** `packages/app` permanece como membro do workspace só até a separação em repositório próprio, e é instalada apenas no grupo de desenvolvimento.

## Alternativas consideradas

- **Manter os cinco pacotes:** isolamento por distribuição, mas cinco arquivos de configuração e mais árvore para ler, sem consumidor externo que justifique.
- **Dois pacotes (ingestão e transformação):** não resolve a duplicação do `core` nem o custo de configuração.

## Consequências

- Imports passam a `plataforma_dados.<subpacote>`; a variável de ambiente do dbt passa a `PLATAFORMA_WAREHOUSE_FILE`.
- O diretório do repositório e o nome no GitHub serão renomeados (`plataforma_dados`) depois da separação da aplicação.
- A raiz ainda contém o pacote `quem_decidiu` da feature 001 (ambiente), que sai com a aplicação.
- Próximos passos: separar a aplicação, PostgreSQL como camada de consumo com macros de portabilidade no dbt, trilha de documentos e vetores (pgvector atrás de uma interface mínima, trechos relacionais como fonte da verdade), Senado.
