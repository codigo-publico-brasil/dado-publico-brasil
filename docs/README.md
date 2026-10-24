# Documentação da plataforma de dados

Índice e regra de organização de `docs/`. Todo documento novo entra em uma das pastas abaixo.

| Pasta | O que guarda | Arquivos |
| --- | --- | --- |
| `dados/` | Como os dados são tratados e o que sabemos sobre eles | [`camadas.md`](dados/camadas.md), [`especificacao-de-fonte.md`](dados/especificacao-de-fonte.md), [`catalogo.md`](dados/catalogo.md) (gerado), [`identidade-de-pessoas.md`](dados/identidade-de-pessoas.md), [`governanca.md`](dados/governanca.md), [`cobertura-e-lacunas.md`](dados/cobertura-e-lacunas.md) (inclui o relatório de pendências de dados), [`auditoria.md`](dados/auditoria.md), [`fontes-de-dados.md`](dados/fontes-de-dados.md), [`observabilidade.md`](dados/observabilidade.md) |
| `dominio/` | O que as instituições são e as regras por trás dos campos (material didático) | [`camara-dos-deputados.md`](dominio/camara-dos-deputados.md), [`senado-federal.md`](dominio/senado-federal.md), [`tse.md`](dominio/tse.md), [`normas-vetos-e-constituicao.md`](dominio/normas-vetos-e-constituicao.md), [`emendas-bens-e-votos.md`](dominio/emendas-bens-e-votos.md) |
| `engenharia/` | Como o sistema é construído | [`arquitetura.md`](engenharia/arquitetura.md), [`arquitetura-producao.html`](engenharia/arquitetura-producao.html) (desenho de produção: dados e infraestrutura, sem fixar provedor) |
| `adr/` | Decisões de arquitetura aceitas, uma por arquivo | [`0001`](adr/0001-fases-e-portoes.md) a [`0019`](adr/0019-dou-so-no-landing.md) |
| `planejamento/` | Raciocínio e plano de longo prazo, de quando o projeto era um só (consulta) | [`plano-de-implementacao.md`](planejamento/plano-de-implementacao.md) |

## Regras

1. **Um assunto, um lugar.** Antes de criar um arquivo, procure se o assunto já tem um.
2. **Itens e pendências ficam no quadro do GitHub**, não em arquivos `.md`.
3. **Uma decisão aceita não é editada**: vira um ADR novo que a substitui.
4. **Todo documento começa dizendo para quem é e o que responde.**
5. **O catálogo (`catalogo.md`) é gerado** (`uv run plataforma catalog`); um teste falha se estiver desatualizado.
6. Documentos de produto da aplicação ficam em [`../../quem-decidiu/docs/`](../../quem-decidiu/docs/README.md). Os specs antigos estão fora dos repositórios (a refazer).
