**Quanto menos código e menos estrutura, melhor; seja sucinto, mas resolva o problema da melhor forma. Proponha antes de executar.**

Este repositório é a camada de dados do projeto Código Público Brasil (dado-publico-brasil). Ele é independente: a aplicação [quem-decidiu](https://github.com/codigo-publico-brasil/quem-decidiu) vive em outro repositório e lê só o esquema `marts`.

**Nomes e descrições:** antes de criar ou alterar tabela ou coluna, leia `docs/engenharia/convencao-de-nomes.md` (tema na frente; colunas `id_`, `dt_`, `fl_`; toda tabela e coluna descrita). Os dados precisam ser auditáveis pelo público: sempre rastreáveis até a fonte.

Pendências, melhorias e decisões abertas são **issues deste repositório**, não arquivos `.md`.

@AGENTS.md

Antes de qualquer tarefa, leia `README.md` e `docs/dados/camadas.md`. Consulte conforme a tarefa: `docs/adr/` (decisões aceitas) e `docs/dados/`.
