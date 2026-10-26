# Arquitetura (resumo)

> **Estado atual da camada de dados:** implementada e documentada em [`docs/01-entender/03-camadas.md`](03-camadas.md) (ADRs [0004](../05-decisoes/0004-camadas-da-plataforma-de-dados.md) a [0012](../05-decisoes/0012-dataset-por-item-lotes-com-envelope.md): dlt, dbt-core, Dagster e DuckDB; motores de ingestão e de transformação em subpacotes de um só pacote). O restante deste resumo continua sendo proposta.

Resumo das camadas e das decisões propostas. As decisões viram ADRs aceitos conforme forem tomadas; até lá, tudo aqui é **proposta**. O raciocínio completo, com alternativas e custos, está em `docs/99-historico/plano-de-implementacao.md`.

## Cinco camadas

1. **Ingestão:** coleta idempotente das fontes oficiais (Câmara, Senado, depois município de São Paulo), com testes de contrato.
2. **Memória:** camada bruta imutável (original, hash, URL, data de captura), camada curada reproduzível, busca por texto e por vetores e, se necessário, um grafo de relações (proposição, autor, votação, voto, partido).
3. **Explicação:** assistente com recuperação de trechos, resposta só com base neles e citação obrigatória. Sem fonte, diz que não encontrou. Entra na fase 4.
4. **Ação coletiva e canais:** portal web sem login, cartões de compartilhamento e, depois, conta opcional com alertas.
5. **Transversais:** governança (neutralidade, LGPD, auditoria) e soberania e segurança (código aberto, mínimo de dependências, modelo substituível).

## Decisões propostas (a registrar em ADR)

| Decisão | Proposta para o piloto |
| --- | --- |
| Armazenamento | Objetos S3-compatíveis para originais com hash, e PostgreSQL para dados curados |
| Pipelines | Dagster para ativos de dados e dbt-core para transformações em SQL |
| Busca | Texto completo e pgvector no próprio PostgreSQL |
| Modelos de IA | Interface própria sobre o modelo, com um modelo aberto testado em paralelo |
| Web | Páginas renderizadas no servidor, cacheadas em CDN, com URL permanente por entidade |
| Mensagens | E-mail e Telegram primeiro; WhatsApp depois |
| Identidade | Link por e-mail ou conta do Telegram, sem login gov.br |
| Licença | AGPL-3.0 no código e CC BY 4.0 nos dados curados (a confirmar) |
| Hospedagem | Uma VM em nuvem brasileira, Docker Compose e infraestrutura como código; Kubernetes só na fase 6, se justificar |

## Forma do código

Monolito modular, um repositório, com módulos de fronteira explícita: ingestão, curadoria, API, web, assistente e notificações. Um módulo só vira serviço separado quando uma medição justificar.

## Regras de dados

- Camada bruta nunca é sobrescrita.
- Camada curada é derivada do bruto, reproduzível e carrega a versão do código que a gerou.
- Contratos de dados e testes em cada ativo; teste falho bloqueia a publicação.
- Reconciliação com os totais da própria fonte.
- Linhagem: de qualquer número na tela ao documento original em até três cliques.
- Pipelines idempotentes.
