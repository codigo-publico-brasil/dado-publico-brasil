# ADR 0003: Ferramentas de segurança do CI

- **Status:** proposto
- **Data:** 2026-10-20
- **Origem:** feature 001, tarefa T002 (`specs/001-ambiente-reproduzivel-ci/`)
- **Contexto do projeto:** uma pessoa desenvolvendo com apoio de agentes de IA. A porta de qualidade precisa barrar dependência vulnerável, listar componentes por versão, medir a saúde de segurança do repositório e propor atualizações, sem custo de licença e com o mínimo de dependências.

## Contexto

A especificação da feature 001 exige: auditoria de dependências que **reprove o PR em severidade alta ou crítica e apenas registre as demais** (FR-005 e FR-008), lista de componentes (SBOM) por versão (FR-011), medição periódica de segurança (FR-012) e atualização de dependências por PR separado (FR-010). A pesquisa da feature (`research.md`, D3 a D7) trazia escolhas provisórias. Esta decisão as confirma ou corrige com chamadas reais. O repositório é privado até o fim da Fase 1.

## Evidências (chamadas reais, 2026-10-20)

| Verificação | Resultado |
| --- | --- |
| `uv export --format cyclonedx1.5` sobre o `uv.lock` do projeto (uv 0.13.1) | Gerou SBOM no formato CycloneDX 1.5 com 13 componentes, sem ferramenta extra. A documentação da uv diz que o formato existe desde a versão 0.9.11. |
| `pip-audit` (PyPA, Apache-2.0) sobre as dependências exportadas | Funcionou, sem vulnerabilidades no projeto. **Não lê `uv.lock`** (exige exportar para `requirements`). Em um arquivo com versões antigas de propósito, devolveu 37 vulnerabilidades, e o JSON traz só `id`, `aliases`, `fix_versions` e `description`: **não traz severidade**. O código de saída é 1 em qualquer vulnerabilidade, sem filtro por severidade. |
| OSV-Scanner v2.6.0 (Google, binário), hash conferido com o `osv-scanner_SHA256SUMS` da própria versão | **Lê `uv.lock` direto** (14 pacotes). Código de saída 0 sem vulnerabilidades e 1 com vulnerabilidades. No mesmo arquivo de teste, o JSON agrupa 19 vulnerabilidades e cada grupo traz `max_severity` com a nota CVSS (por exemplo `8.6`, `5.4`): 9 grupos com nota de 7,0 a 8,9, 10 abaixo de 7,0, nenhum sem nota. |
| Documentação do Dependabot e da uv | O Dependabot suporta o ecossistema `uv` e atualiza o `uv.lock`, com restrições registradas: não relaxa limites de versão fixados à mão em `pyproject.toml`, e o modo de atualizar só o lockfile tem relatos de falha. |
| Documentação da ação OpenSSF Scorecard | É gratuita para repositório público. Em repositório privado, a ação exige o GitHub Advanced Security, e a publicação do resultado fica desligada. A linha de comando do Scorecard roda sem a ação. |

## Decisão

| Área | Escolha |
| --- | --- |
| Auditoria de dependências | **OSV-Scanner**, binário fixado por versão e conferido por hash, lendo `uv.lock`. Um script curto do projeto (biblioteca padrão) lê o JSON e **reprova quando algum grupo tem `max_severity` igual ou maior que 7,0** (alta ou crítica, pela escala CVSS). As demais ficam registradas no resultado do job. Sem nota de severidade, a vulnerabilidade é registrada e **não** reprova (decisão a confirmar pelo fundador, abaixo). |
| Lista de componentes (SBOM) | **`uv export --format cyclonedx1.5`**, gerado no fluxo de release e anexado à versão. Nenhuma ferramenta nova. |
| Medição de segurança | **OpenSSF Scorecard pela linha de comando**, em fluxo agendado semanal, com resultado salvo como artefato do fluxo. A publicação do resultado fica desligada enquanto o repositório for privado e passa a ser avaliada quando ele ficar público (feature 003). |
| Atualização de dependências | **Dependabot** com o ecossistema `uv`, um PR por atualização, passando pela mesma porta e por revisão humana. |
| Segredos | Continua o binário do gitleaks, com versão e hash fixados (tarefa T022 da feature 001). |
| Leitura de YAML nos testes de política | **PyYAML**, só como dependência de desenvolvimento, e `types-PyYAML` para o mypy em modo estrito. |

## Dependências novas aprovadas por este ADR (quando aceito)

| Dependência | Onde | Papel |
| --- | --- | --- |
| OSV-Scanner (binário, v2.6.0) | CI (Linux) | auditoria de dependências |
| OpenSSF Scorecard (binário, versão a fixar na tarefa T032) | CI agendado | medição de segurança |
| PyYAML e `types-PyYAML` | desenvolvimento | testes de política dos arquivos de CI |

Dependabot e `uv export` já fazem parte do que está disponível no GitHub e na uv aceita pelo ADR 0002.

## Alternativas consideradas

- **`pip-audit` para a auditoria:** descartado porque não lê `uv.lock` e não traz severidade, o que impede cumprir FR-008 sem um segundo serviço. Seria necessário consultar uma base de vulnerabilidades por conta própria para obter a nota.
- **Reprovar em qualquer vulnerabilidade (sem filtro de severidade):** mais simples e mais rígido, mas contraria a decisão do fundador de 2026-10-19 (alta e crítica reprovam; as demais ficam registradas) e pode travar o fluxo de uma pessoa só por avisos de baixo risco.
- **Gerador de SBOM de terceiros (por exemplo, o `cyclonedx-py` ou um `uv-sbom` externo):** descartado porque a `uv` já gera CycloneDX 1.5, sem dependência nova.
- **Ação oficial do Scorecard:** descartada por ora porque exige o GitHub Advanced Security em repositório privado.
- **Renovate no lugar do Dependabot:** mais configurável, mas é um serviço a mais; o Dependabot já cobre `uv`.
- **Alertas de dependência do GitHub (Dependabot alerts) como porta:** avisam, mas não são uma checagem que reprova o PR.

## Consequências

- O job `dependencias` baixa um binário em cada execução. O hash dele é conferido no CI contra o valor registrado no repositório, para fechar o risco de cadeia de suprimentos. A versão do binário só muda por PR revisado.
- A regra "alta ou crítica reprova" passa a depender da nota CVSS que a base OSV fornece. Vulnerabilidade sem nota não reprova, e isso é registrado como risco aceito na lista de riscos da feature 003.
- O SBOM não exige instalar nada, mas depende de a versão da `uv` no CI ter o formato (0.9.11 ou mais nova). A versão da `uv` é fixada no CI.
- O Dependabot pode propor atualizações que a `uv` não consegue resolver; o teste `uv lock --check` no CI e a revisão humana cobrem esse caso.
- O Scorecard em repositório privado só roda pela linha de comando e algumas verificações dele não se aplicam; o resultado completo passa a existir quando o repositório ficar público.
- Depois de aceito, este ADR não é editado: mudanças viram um ADR novo que o substitui.

## Pontos para o fundador aceitar

1. **Vulnerabilidade sem nota de severidade** não reprova o PR, só é registrada. Aceita?
2. **Dependências novas listadas acima.** Aceita?
3. **Scorecard fica para o repositório público** na parte de publicação do resultado. Aceita?
