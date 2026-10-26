# ADR 0011: Buscar, ler e código próprio por fonte; chaves por fonte; Senado

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Complementa:** [ADR 0008](0008-motores-separados-e-organizacao-por-poder-e-esfera.md) (captura flexível por adaptador) e [ADR 0010](0010-duas-pastas-env-e-specs-fora.md). Mantém as declarações em `sources/` na raiz da plataforma: o `src/` só tem código.

## Contexto

A ingestão só sabia baixar CSV anônimo por URL, e o ponto onde isso acontece estava misturado ao plano e ao registro de capturas. O Senado (API REST, JSON aninhado) mostrou que a estrutura precisava de pontos de extensão claros. O fundador pediu uma estrutura que garanta flexibilidade (API REST, CSV, credenciais, arquivos compactados, robôs), com o código específico de uma fonte na sua pasta e o comum no geral, sem implementar agora o que nenhuma fonte exige.

## Decisão

1. **Três passos por dataset, cada um em um lugar:**

| Passo | Onde | O que faz |
| --- | --- | --- |
| buscar | `ingestion/fetch.py` | obtém os bytes: HTTP com nova tentativa (falha de rede e 5xx), cabeçalhos do YAML, pergunta barata (HEAD) |
| guardar | `ingestion/landing.py` | landing com hash e registro da captura (igual para toda fonte) |
| ler | `ingestion/read.py` | transforma o arquivo em registros: `csv` e `json` (caminho dos registros, objetos achatados, listas viram tabelas filhas) |

2. **Código próprio só quando preciso:** `ingestion/custom/<poder>/<esfera>/<fonte>.py`, espelhando a árvore de `sources/`. Pode definir `download(url, folder)`, `head(url)` e `records(file, dataset)`; o que não definir segue o padrão. É por aí que entram SOAP, robô (RPA) e pacote compactado: a saída de `download` é sempre um arquivo com hash, então o resto do pipeline não muda. Câmara e Senado não têm módulo próprio.
3. **Credenciais por variável de ambiente:** o YAML só diz onde vai (`headers: {Authorization: "Bearer ${TOKEN}"}`); o valor vem do `.env` ou da infraestrutura. Variável ausente é erro, e segredo nunca entra no repositório.
4. **JSON:** `records` aponta a lista; `nested` nomeia os campos que são listas (viram tabelas filhas no raw); os demais campos entram como texto (o dbt converte), assim a coluna existe mesmo que venha toda vazia.
5. **Várias fontes no pipeline:** `dado-publico run` percorre todas as fontes de `sources/` (`--source` escolhe uma) e o Dagster gera os ativos de cada fonte a partir da declaração.
6. **Chaves por fonte:** os ids da fonte são únicos só dentro da fonte (`2265603-37` na Câmara, `6820` no Senado). Os marts mantêm o id original e a chave é `(fonte, id)`: testes singulares no lugar dos genéricos `unique` e `relationships` nas colunas de id. Quem consome junta também por `fonte`. (A alternativa, prefixar o id, foi descartada: muda todos os valores e os consumidores.)
7. **Identidade com várias fontes:** o modelo `int_pessoas_ids_vistos` reúne os identificadores de todas as fontes, e a resolução cria uma pessoa por identificador novo. **Nunca se liga por nome**: quem foi deputado e senador tem, por ora, duas chaves de pessoa (lacuna documentada); a ligação virá por identificador oficial comum, com confirmação.
8. **Escopo do Senado:** senadores (cadastro, mandatos em tabelas filhas do raw), votações em plenário com votos nominais desde 1999 e as matérias citadas nas votações. Fica para depois: autoria e tramitação de matérias (uma chamada por matéria), detalhes pessoais (uma chamada por senador), votos de comissões e a exposição dos mandatos e exercícios oficiais, que já estão no raw.

## Consequências

- Fonte nova que seja arquivo ou API que devolve CSV ou JSON entra só com YAML e modelos dbt; a que precisar de outro jeito ganha um módulo em `custom/`.
- O raw do Senado é `raw_federal_senado` (`senadores`, `votacoes`, `votacoes__votos` e as tabelas filhas dos mandatos).
- `marts.pessoas` ganha `fonte` e `qtd_propostas` vazio onde a fonte não informa autoria (vazio não é zero); `marts.votacoes` ganha `votacao_secreta`; `marts.mandatos` ganha `fonte`.
- Votação secreta no Senado traz a sigla `Votou` no lugar da escolha: o voto individual não é revelado e fica como a fonte informa.
- Lacuna na fonte: 2015 e 2016 têm pouquíssimas votações (17 e 13, contra cerca de 120 por ano nos demais).
