# Plano de Implementação do Quem Decidiu

> Documento de planejamento do fundador, exportado do documento de trabalho. As regras do dia a dia estão em `AGENTS.md`; este arquivo explica o raciocínio por trás das decisões. Mudanças estruturais viram ADR em `docs/adr/`.


Oct 17, 2026 · @Felipe

## Resumo

O projeto Quem Decidiu, da organização Código Público Brasil, responde a uma pergunta simples com dados oficiais: quem propôs, quem votou e quem aprovou cada decisão, com os partidos envolvidos e o link para o documento original. Começa pequeno: as decisões nacionais, que não dependem de estado ou cidade, mais o município de São Paulo. Em cima dessa base vêm o portal aberto sem login, o assistente que cita as fontes e, por último, a conta opcional com alertas. Não haverá ranking de políticos nem recomendação de voto, e isso será verificado por teste automatizado. Você desenvolve sozinho com o Claude Code, num fluxo ágil sem datas: sete fases, cada uma encerrada por um portão verificável, e uma fase futura de previsão de votos tratada com cautela.

**Decisões que dependem de você**

- Checar a disponibilidade dos nomes Quem Decidiu e Código Público Brasil (a organização já foi criada no GitHub como codigo-publico-brasil; faltam domínio, redes e INPI) (GitHub, domínio, redes e INPI).
- Figura jurídica (associação, projeto sob guarda-chuva ou pessoa física no início).
- Licença: AGPL-3.0 para o código e CC BY 4.0 para os dados curados são uma proposta.
- Se a previsão de votos, quando chegar a hora, cobre só partidos e blocos ou também parlamentares.
- Advogado para revisar a LGPD antes de abrir contas.

## Objetivo, princípios e escopo

A plataforma é um acervo público e consultável de dados sobre o poder público brasileiro, aberto a qualquer pessoa sem login, com conta opcional apenas para receber alertas.

**Princípios que valem para todas as fases**

- **Acesso sem barreira.** Toda consulta funciona sem cadastro. A conta existe só para alertas e preferências.
- **Fonte primária sempre.** Cada dado e cada resposta do assistente apontam para o documento original, com a data de captura.
- **Auditável por construção.** Dado, código, modelo e prompt têm versão e histórico públicos.
- **Compartilhamento sem rastreio.** Os botões geram links simples, com cartão de pré-visualização e o menu de compartilhar do aparelho. Não há SDK de rede social na página.
- **Dados mínimos.** Sem anúncios, sem venda de dados e sem páginas sobre pessoas privadas.

**Escopo da primeira versão**

| Dentro | Fora, por enquanto |
| --- | --- |
| Decisões nacionais, que não dependem de estado ou cidade: proposições, autoria, votações, voto de cada parlamentar e partidos | Ranking, nota ou lista ordenada de políticos, em nenhuma fase |
| Páginas permanentes por decisão, parlamentar e partido, com busca e cartões de compartilhamento | Recomendação de voto, em nenhuma fase |
| Município de São Paulo (só o município): Câmara Municipal e diário oficial | Previsão de votos (fase futura, com condições) |
| Assistente que responde citando a fonte | Cobertura de diários oficiais de todos os municípios |
| Conta opcional com alertas por Telegram e e-mail | Alertas por WhatsApp (depois, por custo e regras da plataforma) |
| Links de compartilhamento | Integração com APIs de redes sociais, comentários abertos |

## Fases, marcos e critérios de saída

São sete fases em sequência e não há datas. O ritmo é um fluxo contínuo de fatias pequenas, e cada fase só termina quando passa um portão verificável. Com você sozinho, usando o Claude Code, cerca de 10 horas por semana, é o portão que decide quando avançar, não o calendário.

*(O diagrama das fases está na tabela de fases do `README.md`.)*

A fase de decisões históricas vem primeiro de propósito: o portal, o assistente e os alertas dependem de números que cheguem ao documento original. As metas de avaliação da fase 4 são definidas na fase 0.

## Primeiro entregável: quem decidiu o quê

A primeira versão responde a uma pergunta simples: quem propôs, quem votou e quem aprovou cada decisão. Para cada proposição (lei, PEC, medida provisória), a página mostra a autoria formal, a tramitação, cada votação, o voto de cada parlamentar, a orientação das bancadas, o resultado e a norma que resultou, sempre com link para o documento oficial.

| Fonte | O que oferece | Limite a verificar |
| --- | --- | --- |
| Câmara dos Deputados, dados abertos | Proposições (todas desde 2001; alguns tipos de 1946 a 2000; algumas de 1934 a 1945), autores, votações, voto de cada deputado e orientação de bancada (só plenário). Arquivos anuais em CSV e JSON, atualizados diariamente | A página não diz desde que ano há votos individuais. Votações simbólicas podem não ter voto por pessoa |
| Senado Federal, dados abertos | Matérias, autorias e relatorias, votações de plenário | Cobertura histórica e voto nominal não confirmados; conferir o catálogo em CSV |
| Decisões antigas, como a criação do Bolsa Família | Podem não existir como dado estruturado | Curadoria manual a partir do Diário Oficial e dos diários do Congresso, marcada como curadoria manual e com a fonte |

**Casos de teste.** Alguns casos conhecidos servem de gabarito para o pipeline e para a página.

- Fim da escala 6x1: segundo uma reportagem do jornal O Povo, o texto reuniu a PEC 221/2019 e a PEC 8/2025, veio da Câmara em maio de 2026, e a CCJ do Senado o aprovou em 2 de setembro de 2026 por votação simbólica, com quatro senadores contrários. O plenário do Senado ficou para depois do primeiro turno das eleições. É uma única fonte, a situação pode ter mudado, e o placar da Câmara não foi confirmado; o gabarito deve vir dos dados oficiais.
- Bolsa Família: quem criou, quem relatou e quem votou precisam ser levantados nas fontes oficiais antes de entrar. Nada disso foi pesquisado aqui.

**Regras de apresentação.** "Propôs" significa autoria formal registrada. "Aprovou" significa voto registrado. Votação simbólica aparece como "sem voto individual". A ordem é sempre cronológica ou alfabética, o modelo de página é o mesmo para todos os partidos e não há adjetivos.

## Linhas vermelhas e fase futura de previsão

**Linhas vermelhas.** Não haverá ranking, nota nem lista ordenada de políticos por qualquer medida avaliativa, e não haverá recomendação de voto. Isso vira teste automatizado: o CI falha se uma página ou consulta ordenar parlamentares por métrica de desempenho, e a avaliação do assistente inclui pedidos como "quem é o melhor deputado", que ele deve recusar.

**Fase futura: "se esta lei fosse votada hoje".** É possível tecnicamente, mas é a parte mais arriscada do projeto para a neutralidade. Os modelos tendem a repetir a orientação da bancada, e uma lista de quem "votaria não" pode ser lida como rótulo ou ranking. Minha sugestão é subir em três degraus e só passar ao seguinte se o anterior estiver aprovado:

1. **Projetos parecidos.** Dado um texto, listar proposições semelhantes do passado e como cada partido e bancada votou. É busca, sem probabilidade.
2. **Padrões por partido e bloco.** Frequência histórica em votações semelhantes, com o número de casos e a incerteza à vista.
3. **Probabilidade.** Só com teste em dados de período posterior ao do treino, calibração, comparação com uma regra simples (seguir a orientação da bancada) e metodologia publicada.

Partidos e blocos entram. Parlamentares individuais ficam de fora no início; essa é uma decisão sua, listada nas decisões em aberto. A fase só começa depois dos portões 1 a 4, com revisão do conselho plural e do jurídico.

## Gestão do projeto na era da IA

Você será produto, arquitetura e revisão; o Claude Code executa. Sem datas, o ritmo vem de um quadro de fluxo com poucos itens em andamento. As práticas abaixo são sugestões minhas, não pesquisadas em fonte.

| Prática | Como aplicar | O que você treina |
| --- | --- | --- |
| Fluxo com limite | Colunas: Backlog, Pronto para o agente, Em andamento (máximo 2), Em revisão, Feito | Gestão de fluxo e foco |
| Fatias verticais finas | Cada item entrega algo visível de ponta a ponta, como uma proposição com autoria e votos na página | Quebrar escopo |
| Item pronto para o agente | Contexto, critério de aceite testável, o que fica fora, arquivos que pode tocar. Sem isso o item não entra | Especificação como habilidade central |
| Definição de pronto | Testes e portões de dado passam, você revisou, ADR se a decisão é estrutural | Qualidade sem depender de confiança |
| Revisão semanal de 30 minutos | O que entregou, onde o agente errou, o que muda no AGENTS.md. Erro recorrente vira regra ou teste | Melhoria contínua do processo |
| Métricas simples | Tempo de ciclo por item, entregas por semana, parcela dos PRs do agente que voltam para correção, falhas após a entrega | Gerir por evidência |
| Backlog e roadmap públicos | Issues e ADRs no repositório; o roadmap mostra portões, não datas | Transparência como método |

O gargalo passa a ser a sua revisão, não a escrita de código. Reserve blocos de tempo para revisar e não aceite mudanças que você não entende.

## Nomes e alcance

**Organização.** Código Público Brasil, criada no GitHub como codigo-publico-brasil. O nome é neutro, diz que código e dados são de todos e lembra o movimento "Public Money, Public Code". O endereço é longo, então domínio e redes devem usar uma versão curta. A organização pode ter repositórios separados: o app, os dados e pipelines, a metodologia com a avaliação, e o guia de contribuição.

**Projeto.** Quem Decidiu. É a pergunta que o produto responde e serve de nome, slogan e endereço (por exemplo, "quemdecidiu" seguido do tema). "Radar Público" pode ficar como nome do módulo de alertas.

**Não verifiquei a disponibilidade.** Não consegui consultar o GitHub a partir desta sessão, e as buscas na web foram inconclusivas. Antes de anunciar, confira GitHub, domínio .org.br ou .br, nomes nas redes e o registro no INPI.

**Espalhar sem sair da neutralidade.** Um cartão de compartilhamento padrão ("Quem decidiu \[tema\]?") gerado no dia de cada votação importante, linguagem simples, páginas permanentes que funcionem em celular básico e parceiros de checagem que republiquem. O projeto não otimiza por indignação nem por engajamento.

## Arquitetura e decisões

O desenho em cinco camadas está no [diagrama de arquitetura](https://claude.ai/artifact/6P7f6Gbt7sLYo1khSCjLU6); estas são as nove decisões que merecem registro formal (ADR) antes do primeiro código, cada uma com a recomendação para o piloto.

| Decisão | Recomendação para o piloto | Alternativa | O que a escolha custa |
| --- | --- | --- | --- |
| Armazenar dados | Objetos S3-compatíveis para originais imutáveis (com hash) e PostgreSQL para dados curados | Lakehouse com Parquet e Iceberg | Um Postgres basta enquanto o volume do piloto couber nele; é hipótese a medir na fase 1 |
| Orquestrar pipelines | Dagster para ativos de dados e dbt-core para as transformações em SQL | Airflow, ou scripts agendados | Dagster trata cada tabela como ativo com testes e linhagem; a curva de aprendizado é maior que a de um cron |
| Buscar | Texto completo e pgvector no próprio PostgreSQL | OpenSearch | Um serviço a menos para operar; troca-se quando relevância ou volume exigirem |
| Modelos de IA | Interface própria sobre o modelo. Usar o que passar na bateria de avaliação e manter um modelo aberto testado em paralelo | Fixar um fornecedor | A interface custa um adaptador e entrega saída de emergência e controle de privacidade |
| Web | Páginas renderizadas no servidor, cacheadas em CDN, com URL permanente por entidade | SPA com API | Abrem rápido em celular simples, são compartilháveis e indexáveis |
| Mensagens | E-mail e Telegram na fase 5; WhatsApp depois | WhatsApp primeiro | O WhatsApp exige template aprovado para mensagem iniciada por você e [cobra por mensagem de template entregue](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing) |
| Identidade | Link único por e-mail ou conta do Telegram | Login gov.br | Evita amarrar a plataforma ao governo; a verificação é mais fraca contra abuso |
| Licença | AGPL-3.0 no código e CC BY 4.0 nos dados curados | MIT | A AGPL impede apropriação fechada de uma instância e afasta alguns parceiros |
| Hospedagem | Uma VM em nuvem brasileira, com Docker Compose e infraestrutura como código | Kubernetes desde o início | Kubernetes é aprendizado, não necessidade do piloto; entra na fase 6 |

**Forma do código.** Monolito modular: um repositório, com módulos de fronteira explícita (ingestão, curadoria, API, web, assistente, notificações). Um módulo vira serviço separado só quando uma medição justificar.

**Como registrar.** Um arquivo ADR por decisão, no repositório, com contexto, opções, decisão, consequências e data. Depois de aceito, ele não é editado: a mudança vira um ADR novo que o substitui.

## Acesso, contas, notificações e compartilhamento

Todo conteúdo é público e cacheável; a conta guarda apenas um canal de contato e uma lista de assuntos seguidos.

**Acesso anônimo**

- Cada parlamentar, proposição, contrato e ato de diário oficial tem uma página com endereço permanente, servida por CDN.
- A busca e o assistente funcionam sem cadastro. A medição de uso é agregada e sem cookie de rastreio.
- Quem quiser citar uma página usa o endereço com a data de captura (por exemplo, `?v=2026-10-17`), para o link apontar sempre para a mesma versão.

**Conta opcional**

- Criação por link único enviado por e-mail ou pelo bot do Telegram. Não pede nome nem CPF.
- Guarda só o canal, os assuntos seguidos e a data do consentimento.
- Descadastro e exclusão em um clique, em qualquer mensagem.

**Notificações**

- O padrão é um resumo semanal por assunto; alerta imediato é escolha explícita, com limite de frequência.
- Exemplos de assunto: uma votação marcada para um parlamentar, uma emenda nova para um município, um ato novo no diário oficial com um termo.
- Toda mensagem traz a fonte, a data de captura e o link para cancelar.

| Canal | Quando entra | Custo e regra | Observação |
| --- | --- | --- | --- |
| E-mail | Fase 5 | Custo baixo no provedor; exige SPF, DKIM e DMARC configurados | Base do sistema, sem depender de plataforma de mensagens |
| Telegram | Fase 5 | Bot gratuito. A [FAQ de bots](https://core.telegram.org/bots/faq) indica cerca de 30 mensagens por segundo em envios em massa e evitar mais de uma por segundo no mesmo chat | A adesão do público-alvo precisa ser medida no piloto |
| Web Push (PWA) | Fase 5, opcional | Sem conta; depende da permissão do navegador | A confirmar no piloto, principalmente no iPhone |
| WhatsApp | Depois da fase 5, se a medição justificar | Desde 1º/7/2025 a [cobrança é por mensagem de template entregue](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing). Mensagem iniciada pela plataforma exige template aprovado. Resposta sem template só vale dentro da janela de 24 horas aberta pelo usuário | Desenho possível: a pessoa envia "oi" e recebe o resumo na janela aberta. Alerta fora da janela é template pago. Os valores em BRL estão numa tabela da Meta que não consegui ler, então orçar só depois de consultá-la |

**Compartilhamento sem integração**

1. Link permanente com título e descrição curtos e cartão de pré-visualização (Open Graph), para o link ficar legível em qualquer rede.
2. Botão que abre o menu de compartilhar do aparelho (Web Share API), com cópia do link como alternativa.
3. Imagem gerada no servidor com a afirmação, a fonte e a data, para a informação viajar com o comprovante.

A página não carrega script nem pixel de rede social.

## Desenvolvimento com IA, testável e auditável

A regra central: a IA propõe e o processo decide. Nada vai para produção sem um teste que falharia sem a mudança, um humano que leu o diff e um registro de quem escreveu o quê.

O projeto tem dois tipos de IA, e cada um precisa de um regime próprio.

|  | IA que escreve o código | IA dentro do produto |
| --- | --- | --- |
| Risco principal | Código errado ou inseguro que passa despercebido | Resposta errada com aparência de autoridade |
| Controle principal | Testes, revisão humana e porta de CI | Citação obrigatória, recusa sem fonte e avaliação contínua |
| Evidência que fica | PR com testes, autoria registrada e ADR | Traço de cada resposta e conjunto de avaliação versionado |

**Fluxo de cada mudança**

1. Especificação curta no repositório: problema, critérios de aceite verificáveis e o que a mudança não faz. A IA recebe a especificação, não só uma conversa.
2. Testes primeiro. A IA escreve os testes a partir dos critérios e você os revisa com mais cuidado que o código, porque eles são o contrato.
3. Implementação em mudança pequena: um PR por assunto, com limite de tamanho do diff.
4. Porta de CI que ninguém contorna, em branch protegida: formatação, tipos, testes unitários, de contrato e de dados, avaliação do assistente quando prompt, modelo ou índice mudam, varredura de segredos e dependências, e lista de componentes (SBOM).
5. Revisão humana obrigatória. Código de dados e de segurança pede um segundo par de olhos do grupo (CODEOWNERS).
6. Merge feito por humano e deploy feito só pelo pipeline.

**Controles ao redor do agente de código**

- Um arquivo de instruções do agente (AGENTS.md ou CLAUDE.md) no repositório, versionado e revisado como código: regras do projeto, comandos de teste e o que nunca fazer, como fabricar dados de teste com aparência real ou mexer em migrações sem ADR.
- Ambiente isolado, sem credenciais de produção e sem permissão de escrita na branch principal.
- Campo no PR sobre o que foi escrito por IA, com qual ferramenta e o que você verificou à mão, mais trailer de coautoria nos commits.
- Testes de mutação de tempos em tempos, para checar se os testes pegam falhas de verdade, e testes de propriedade nas transformações de dados. Exemplo: a soma por parlamentar sempre bate com o total da fonte.
- Uma segunda revisão por outro agente, sem o contexto da implementação, só como triagem. A decisão é humana.

**Dados auditáveis**

- Camada bruta imutável: documento original, hash, URL e data de captura, nunca sobrescritos.
- Camada curada derivada do bruto e reproduzível, com a versão do código que a gerou.
- Contratos de dados nas fronteiras (esquema, tipos, nulos, unicidade) e testes em cada ativo. Teste falho bloqueia a publicação do dado.
- Reconciliação contra a própria fonte, com os totais mensais que ela publica, e amostragem manual periódica.
- Linhagem: de qualquer número na tela até o documento original em até três cliques.
- Testes de contrato com respostas gravadas das APIs oficiais, mais uma verificação diária contra a API real para detectar mudança de formato.
- Pipelines idempotentes: rodar de novo não duplica.

**Assistente, a IA no produto**

- Fluxo: recuperar trechos, gerar só com os trechos, citar e verificar a citação. Sem fonte, o assistente diz que não encontrou.
- Conjunto de avaliação de referência versionado, montado com jornalistas parceiros: pergunta, fontes esperadas e resposta aceitável. Mede se a resposta é sustentada pelos trechos, se a citação aponta o trecho certo e se a recusa ocorre quando deve. Ferramentas candidatas: Ragas, promptfoo, Inspect ou DeepEval. As metas numéricas ficam para a fase 0, definidas com os parceiros.
- Neutralidade testada: pares de perguntas espelhadas (mesmo fato, partido ou pessoa diferente), com checagem automática de assimetria e revisão humana.
- Observabilidade: um traço por resposta com pergunta, trechos recuperados, versões do prompt e do modelo, resposta e citações, com anonimização e retenção curta. As convenções de IA generativa do OpenTelemetry cobrem spans, métricas e eventos; não consegui confirmar a estabilidade delas no [repositório](https://github.com/open-telemetry/semantic-conventions-genai), então trate-as como em evolução.
- Segurança: use o OWASP Top 10 para aplicações de LLM 2025 como lista de verificação. A [injeção de prompt é o item LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/). Documentos ingeridos são dados não confiáveis, porque um ato de diário oficial pode conter texto que tenta instruir o modelo. O assistente não tem ferramentas com efeito colateral.
- Transparência: toda resposta é marcada como gerada por IA, com a versão do modelo e os botões "ver fontes" e "reportar erro". Uma página pública mostra o que o assistente ainda erra e as métricas atuais. Cada erro reportado vira um caso do conjunto de avaliação.

**Gestão de risco.** Use o [NIST AI RMF 1.0 e seu perfil de IA generativa (NIST AI 600-1)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence), publicado em 26/7/2024, como roteiro de revisão. Mantenha um registro de riscos vivo no repositório e uma ficha do assistente com propósito, limites, dados e avaliações.

**Pacote de evidências por versão.** A cada release, publique a versão do código e das dependências, os resultados de testes, de dados e de avaliação, as mudanças em prompts e modelos e os riscos abertos. É isso que permite a um terceiro auditar a operação sem confiar na sua palavra.

## Governança e conformidade

A plataforma trata dados de pessoas apenas no papel público delas, e cada regra de neutralidade vira algo que um terceiro consegue verificar. Isto não é parecer jurídico: valide com um especialista em LGPD antes do lançamento.

**LGPD**

- Dado pessoal de acesso público pode ser tratado considerando a finalidade, a boa-fé e o interesse público que justificaram a divulgação, segundo o [resumo do Serpro](https://www.serpro.gov.br/lgpd/menu/protecao-de-dados/dados-publicos-lgpd). Repassar esses dados a outras organizações pode exigir novo consentimento, salvo as hipóteses previstas em lei. A página não define quais dados contam como públicos, tema em debate que caberia à ANPD regulamentar.
- Consequências para o desenho: finalidade escrita e pública (controle social); páginas só de agentes públicos e candidatos, limitadas à atuação pública; nenhuma página ou perfil de pessoa privada, como doadores pessoas físicas, sócios de empresas ou servidores sem cargo de decisão. Doações aparecem agregadas.
- Relatos de moradores: dados mínimos, moderação antes de publicar e remoção a pedido.
- Antes do lançamento: relatório de impacto à proteção de dados, política de privacidade em linguagem simples, canal para os direitos dos titulares e um encarregado definido.

**Regulação de IA**

- O PL 2338/2023 foi aprovado no Senado em 10/12/2024 e está na Câmara. A votação foi adiada para 2026, sem data, e o texto volta ao Senado por causa das mudanças, segundo uma [análise de empresa de compliance](https://confidata.com.br/blog/anpd-regulacao-ia-brasil-2026-2027). A fonte é um blog, não o texto legal; confira no projeto.
- Sistemas fora das categorias de alto risco teriam regulação mais leve, centrada em transparência. Projetar já com rótulo de IA, rastreabilidade e relato de erro evita retrabalho.

**Neutralidade que se verifica**

| Compromisso | Como um terceiro verifica |
| --- | --- |
| Metodologia e critérios publicados antes dos dados | Repositório aberto, com histórico de mudanças datado |
| Mesmo tratamento para todos os partidos | Testes espelhados do assistente e das páginas, com resultados públicos |
| Nenhuma nota nem ranking de políticos | Ausência no produto; qualquer proposta passa por ADR e pelo conselho |
| Financiamento sem dependência | Teto por financiador e lista pública de apoiadores e valores |
| Erros corrigidos à vista | Página pública de correções, com data e o que mudou |
| Direito de fork | Licença aberta e dados curados disponíveis para download completo |
| Conselho plural e auditoria externa | Relatório da auditoria publicado a cada ano |

**Moderação e abuso.** As regras são públicas. Relatos pedem local e evidência, passam por revisão humana antes de aparecer e têm limite por conta.

## Organizações e referências que podem contribuir

O Núcleo Jornalismo e a Open Knowledge Brasil têm a maior sobreposição e a maior alavanca, então são os primeiros contatos. As demais entram conforme cada fase pede.

| Organização | O que já oferece | Como colaborar | Observação |
| --- | --- | --- | --- |
| [Núcleo Jornalismo](https://apublica.org/2026/08/iniciativas-de-jornalismo-lancam-coalizao-para-investigar-desinformacao-eleitoral/) | Jornalismo sobre o impacto da tecnologia. O [Legislatech](https://latamjournalismreview.org/articles/projects-from-independent-outlets-make-it-easier-to-access-information-ahead-of-brazilian-elections/) monitorava em 2024, a cada 30 minutos, documentos públicos de 16 órgãos (processos, projetos de lei, diários oficiais) e enviava alertas por termo, em parceria com o Querido Diário. O [Legislatech AI](https://news.microsoft.com/pt-br/nucleo-lanca-mecanismo-de-busca-com-ia-focado-em-leis-brasileiras-gratuito/), de jun/2025, busca legislação federal e responde com links de referência; os dados estão em repositório aberto e o código no GitHub. Integra o Laboratório de Investigação Eleitoral com Agência Pública, Amado Mundo e Aos Fatos | Dados de legislação federal abertos como fonte; revisão jornalística do conjunto de avaliação do assistente; troca de lições sobre alertas por termo | Em 2024 o Legislatech tinha plano gratuito limitado e planos pagos a partir de R$25. Não verifiquei os planos atuais. Combine antes o que cada lado oferece de graça |
| [Open Knowledge Brasil](https://civictech.guide/projects/embaixadoras) | Mantém o Querido Diário (MIT) e a rede Embaixadoras de Inovação Cívica, criada em 2019 para promover eventos formativos locais | Raspadores dos municípios do piloto, testes e documentação; as embaixadoras como rede local | A página da rede não traz detalhes de inscrição; o contato é por ok.org.br/projetos/embaixadoras |
| [Abraji](https://abraji.org.br/english) | Associação sem fins lucrativos de jornalismo investigativo, de dez/2002. Atua em formação, liberdade de imprensa e acesso à informação. Lista projetos como Comprova, CruzaGrafos, Achados e Pedidos e Aleph | Oficinas para redações usarem a plataforma; validação dos dados com jornalistas; parceria institucional | Não verifiquei o que fazem CruzaGrafos e Aleph. Converse antes de presumir |
| [Transparência Brasil](https://novosite.transparencia.org.br/projetos/excellencies) | Manteve o Excelências de 2006 a 2017, segundo a ONG, e fez o [Achados e Pedidos](https://novosite.transparencia.org.br/projetos/findings-and-requests) com a Abraji, de jul/2016 a dez/2023 | Revisão metodológica das fichas e da moderação; lições do Achados e Pedidos | A página do Achados e Pedidos não diz que acabou, mas o período listado termina em dez/2023. Confirme se a base de pedidos continua disponível |
| [Fiquem Sabendo](https://ijnet.org/pt-br/story/wikilai-enciclop%C3%A9dia-viva-do-acesso-%C3%A0-informa%C3%A7%C3%A3o-p%C3%BAblica-no-brasil) | Agência de dados públicos. Segundo a matéria de lançamento do WikiLAI, envia mais de 2 mil pedidos LAI por ano, oferece oficinas gratuitas e mantém a enciclopédia WikiLAI | Pedidos LAI para cobrir lacunas, como contratos e diários municipais; oficinas; modelos de recurso | A matéria é do lançamento do WikiLAI; confirme o número atual |
| [Aos Fatos e Agência Lupa](https://latamjournalismreview.org/articles/projects-from-independent-outlets-make-it-easier-to-access-information-ahead-of-brazilian-elections/) | Aos Fatos opera o chatbot de checagem Fátima, no site, no WhatsApp e no Telegram. A Lupa publica a Ebulição, que monitora grupos públicos de WhatsApp e Telegram com tecnologia da Palver (dados de 2024) | Experiência de operar bot em mensageiros; padrão de checagem de afirmações; integrar checagens publicadas de várias agências, sem eleger uma só | Os dados são de 2024; confirme os produtos atuais |
| [NetLab (UFRJ)](https://apublica.org/2026/08/iniciativas-de-jornalismo-lancam-coalizao-para-investigar-desinformacao-eleitoral/) | Laboratório de pesquisa da Escola de Comunicação da UFRJ; apoia o Laboratório de Investigação Eleitoral | Avaliação independente de neutralidade e de desinformação; orientação de trabalhos acadêmicos | Não pesquisei os produtos do NetLab |
| [Comunidade Decidim e Brasil Participativo](https://agenciagov.ebc.com.br/noticias/202511/brasil-participativo-integra-comite-internacional-de-democracia-digital) | Decidim é usado por mais de 400 organizações em 30 países. O Brasil Participativo entrou, em nov/2025, no comitê de instituições públicas da comunidade | Contribuir com tradução, acessibilidade e integração; pedir orientação sobre a camada de participação | A AGPL vale para qualquer instância modificada que você hospedar |
| A mapear | Colab (EACH/USP) apareceu como parceiro do Achados e Pedidos em 2018. A Nossas (Rede Nossas Cidades) apareceu numa busca sobre mobilização | A definir | Não verifiquei nenhuma das duas |

**Como abordar**

1. Chegue com um protótipo e a metodologia, não com uma ideia. Um piloto simples com dados reais pesa mais que um documento.
2. Comece pelo Núcleo, para decidir o que integrar e o que não duplicar. O que a sua plataforma acrescenta, como relatos locais e alcance nas periferias, precisa ser confirmado com eles.
3. Faça um pedido concreto por organização. Exemplos: ao Núcleo, revisar o conjunto de avaliação; à OKBR, um raspador de município; à Fiquem Sabendo, um pedido LAI.
4. Ofereça contrapartida: código aberto, dados curados e o relatório de avaliação.
5. Deixe por escrito o crédito, a licença e o que cada lado mantém.

## Plano de aprendizado

Cada fase entrega algo que funciona e ensina uma disciplina; o critério de domínio é uma prova que você consegue fazer, não uma sensação.

| Fase | O que construir | O que aprender | Prova de que aprendeu |
| --- | --- | --- | --- |
| 0. Fundação | Repositório, CI com porta de qualidade, cinco primeiros ADRs, metodologia v0, AGENTS.md, metas de avaliação combinadas com parceiros | Registro de decisões, CI/CD, infraestrutura como código, modelagem de ameaças, quadro de fluxo | Outra pessoa sobe o ambiente do zero seguindo só o README |
| 1. Decisões históricas | Ingestão idempotente da Câmara e do Senado, camada bruta imutável, camada curada, contratos e testes, reconciliação, casos de teste | Engenharia de dados confiável, linhagem, qualidade, testes de contrato | A reconciliação com a fonte passa e reexecutar o pipeline não muda nada |
| 2. Portal | Páginas com endereço estável, busca, cartões de compartilhamento, acessibilidade | Renderização no servidor, cache e CDN, desempenho em rede ruim, acessibilidade (WCAG), Open Graph | Teste com pessoas reais, em celular simples e com leitor de tela |
| 3. São Paulo | Ingestão da Câmara Municipal e do diário oficial, mesma metodologia e mesmos testes | Fontes heterogêneas, extração de diários, reuso de contratos de dados | O mesmo teste de reconciliação roda nas duas camadas |
| 4. Assistente | RAG com citação, conjunto de avaliação, avaliação no CI, traços, testes de segurança, recusa de pedidos de ranking | RAG, avaliação de LLM, observabilidade, segurança de LLM | A avaliação bloqueia um PR que piora a fidelidade, e você prova isso com uma regressão proposital |
| 5. Contas e alertas | Conta sem senha, preferências, filas, e-mail e Telegram, consentimento | Sistemas assíncronos, filas e idempotência, limites de taxa, privacidade na prática | Descadastro e exclusão testados ponta a ponta e reenvio sem duplicar |
| 6. Abertura | Guia de contribuição, auditoria externa, Kubernetes se justificar | Governança de projeto aberto, segurança da cadeia de suprimentos, operação | Uma contribuição externa aceita e o relatório de auditoria publicado |

**Como registrar o aprendizado.** Mantenha um diário técnico por fase: a decisão tomada, a alternativa descartada, o erro cometido e o que mudou. Ele aponta para os ADRs e pode viver no seu vault do Obsidian.

**Leituras-âncora.** NIST AI RMF com o perfil de IA generativa, OWASP Top 10 para LLM, a LGPD, e *Designing Data-Intensive Applications*, de Martin Kleppmann, como fundamento de arquitetura de dados (sugestão minha, não pesquisada aqui).

## Riscos e perguntas em aberto

O maior risco é o escopo. Sem datas, o sinal de excesso é um item que fica muito tempo em andamento; com mais gente o fluxo acelera, e a ordem das fases continua valendo. Os riscos abaixo incluem os que surgiram nesta revisão.

| Risco | Sinal de alerta | Resposta |
| --- | --- | --- |
| Escopo maior que a capacidade | Um item fica semanas em andamento sem entregar | Cortar para um município e um tema; abrir fase nova só com o portão da anterior cumprido |
| Assistente erra com ar de autoridade | Resposta sem citação, ou com citação que não sustenta o que diz | Citação obrigatória, recusa sem fonte, avaliação no CI e rótulo de IA |
| Percepção de viés | Críticas de assimetria entre partidos | Testes espelhados públicos, conselho plural e correções à vista |
| Sobreposição com iniciativas existentes | Um parceiro vê o projeto como concorrente | Integrar antes de construir; começar a conversa pelo Núcleo e pela OKBR |
| Dados pessoais e LGPD | Uma página que identifica pessoa privada | Só atuação pública, doações agregadas, relatório de impacto e revisão jurídica |
| APIs oficiais mudam ou caem | O teste de contrato diário falha | Guardar sempre o bruto, reprocessar e alertar no pipeline |
| Projeto sem manutenção | As atualizações cessam; a Serenata está dormente há cerca de seis anos | Manutenção como entrega de cada fase, documentação, mais de um mantenedor e financiamento diverso |
| Custo de IA e infraestrutura | O custo por consulta sobe | Cache de respostas, limite por usuário e orçamento por fase |
| Abuso e spam nos relatos | Relatos repetidos ou falsos | Limite por conta, revisão humana e evidência obrigatória |

**Riscos acrescentados nesta revisão**

- **Previsão de votos lida como ranking ou rótulo.** Resposta: começar por projetos parecidos, só partidos e blocos, metodologia pública e revisão do conselho plural.
- **Dados históricos incompletos.** Resposta: mostrar "sem voto individual" e "curadoria manual" em vez de preencher lacunas.
- **Buscar alcance e perder a neutralidade.** Resposta: viralizar pela utilidade (a pergunta do dia) e nunca por indignação; o modelo de página é igual para todos os partidos.
- **Revisão superficial do código do agente.** Resposta: item pronto para o agente, definição de pronto e revisão semanal do processo.
- **Nome ou marca já em uso.** Resposta: checar GitHub, domínio, redes e INPI antes de anunciar.

**Decisões que são suas**

- [ ] Os nomes Quem Decidiu e Código Público Brasil estão livres no GitHub, em domínio, nas redes e no INPI?
- [ ] Que entidade abriga o projeto: associação, fundação ou um projeto dentro de uma organização parceira?
- [ ] Licença: AGPL no código e CC BY nos dados, ou outra combinação?
- [ ] A previsão de votos futura cobre só partidos e blocos, ou também parlamentares?
- [ ] Quem faz a revisão jurídica da LGPD?

## Fontes

Páginas consultadas em 17/10/2026, salvo quando indicado. Alguns itens vieram de resultados de busca e não foram abertos na íntegra.

- [Agência Pública: coalizão para investigar desinformação eleitoral (ago/2026)](https://apublica.org/2026/08/iniciativas-de-jornalismo-lancam-coalizao-para-investigar-desinformacao-eleitoral/)
- [Latam Journalism Review: projetos independentes antes das eleições (Legislatech, Fátima, Ebulição)](https://latamjournalismreview.org/articles/projects-from-independent-outlets-make-it-easier-to-access-information-ahead-of-brazilian-elections/)
- [Microsoft News Brasil: Núcleo lança o Legislatech AI (jun/2025)](https://news.microsoft.com/pt-br/nucleo-lanca-mecanismo-de-busca-com-ia-focado-em-leis-brasileiras-gratuito/)
- [Civic Tech Field Guide: Embaixadoras de Inovação Cívica](https://civictech.guide/projects/embaixadoras)
- [Abraji](https://abraji.org.br/english)
- [Transparência Brasil: Excelências](https://novosite.transparencia.org.br/projetos/excellencies) (trecho de resultado de busca)
- [Transparência Brasil: Achados e Pedidos](https://novosite.transparencia.org.br/projetos/findings-and-requests)
- [IJNet: WikiLAI, da Fiquem Sabendo](https://ijnet.org/pt-br/story/wikilai-enciclop%C3%A9dia-viva-do-acesso-%C3%A0-informa%C3%A7%C3%A3o-p%C3%BAblica-no-brasil)
- [Agência Gov: Brasil Participativo e a comunidade Decidim](https://agenciagov.ebc.com.br/noticias/202511/brasil-participativo-integra-comite-internacional-de-democracia-digital)
- [Meta: preços da WhatsApp Business Platform](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- [Telegram: FAQ de bots](https://core.telegram.org/bots/faq)
- [Serpro: dados públicos na LGPD](https://www.serpro.gov.br/lgpd/menu/protecao-de-dados/dados-publicos-lgpd)
- [Confidata: PL 2338/2023 e ANPD](https://confidata.com.br/blog/anpd-regulacao-ia-brasil-2026-2027)
- [NIST: AI 600-1, perfil de IA generativa](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)
- [OpenTelemetry: convenções semânticas de GenAI](https://github.com/open-telemetry/semantic-conventions-genai)
- [OWASP: LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) (resultado de busca, página não aberta)
- [Querido Diário, API no GitHub](https://www.github.com/okfn-brasil/querido-diario-api)
- [Decidim no RubyGems](https://rubygems.org/gems/decidim-participatory_processes)

* [Câmara dos Deputados, dados abertos](https://dadosabertos.camara.leg.br/swagger/api.html): proposições, autores, votações e votos por deputado.
* [Senado Federal, dados abertos](https://www12.senado.leg.br/dados-abertos): matérias, autoria e votações.
* [O Povo, comissão do Senado aprova o fim da escala 6x1 (2/9/2026)](https://mais.opovo.com.br/jornal/economia/2026/09/02/comissao-do-senado-aprova-o-fim-da-escala-6x1-e-materia-vai-a-plenario.html)
