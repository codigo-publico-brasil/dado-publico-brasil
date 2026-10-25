# ADR 0024: Regras de extração por fonte e carga diária só da partição em curso

- **Status:** aceito (2026-10-25, pelo fundador)
- **Data:** 2026-10-25
- **Substitui em parte:** o [ADR 0019](0019-dou-so-no-landing.md), item 4 (o DOU fora da execução diária), e a janela `stable_after_years` do incremental.

## Contexto

O incremental conferia os anos "que ainda podem mudar" de cada dataset (`stable_after_years`: os dois últimos anos na Câmara e os quatro últimos no TSE) e deixava o DOU de fora. Cada fonte tem um ritmo: a Câmara e o DOU mudam todo dia útil; o TSE muda em datas pontuais (eleição, apuração, prestação de contas). Uma execução diária que confere anos antigos, ou que puxa arquivos pesados do TSE sem ninguém pedir, não serve.

## Decisão

1. **A execução diária (`--incremental`) confere só a partição em curso** (o ano, o mês ou a legislatura de hoje) de cada dataset, mais os datasets completos. Tudo que é retroativo exige pedir: `--years` ou `--historical --from-year`.
2. **Cada fonte declara o seu ritmo** no YAML: `refresh: daily` (entra na execução diária) ou `refresh: on_request` (só quando pedido), com padrão por fonte e exceção por dataset. Câmara, Senado, Portal da Transparência, Constituição e DOU são `daily`; o TSE é `on_request`.
3. **O DOU entra na execução diária pelo mês em curso**, como as demais. O zip do mês é reescrito a cada atualização e cada versão fica no landing (imutável), então o landing cresce enquanto o mês durar.
4. **Falha de fonte não derruba a execução:** as buscas próprias de uma fonte (DOU, Constituição) levantam `OSError`, que o plano registra como indisponibilidade e segue.
5. **Sai `stable_after_years`**, que não tem mais função.

## Consequências

- No virar do ano (ou do mês), as últimas alterações do período anterior só entram se alguém pedir o período anterior.
- No começo do mês, o arquivo do DOU do mês novo pode ainda não existir: aparece como indisponibilidade até ser publicado.
- Para atualizar o TSE (por exemplo, na apuração): `dado-publico extract --source tse --years 2026 --dataset candidaturas` e `load`.
- O landing do DOU guarda uma versão por dia no mês em curso; definir uma política de retenção é trabalho futuro.
