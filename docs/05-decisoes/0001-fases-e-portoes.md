# ADR 0001: Trabalhar em fases com portões verificáveis, sem datas

- **Status:** proposto
- **Contexto do projeto:** uma pessoa desenvolvendo com apoio de agentes de IA, com cerca de 10 horas por semana.

## Contexto

O projeto tem muito escopo possível (dados nacionais e locais, portal, assistente, alertas) e poucas horas disponíveis. Prazos fixos tendem a ser estimados mal e a estimular cortes de qualidade. Além disso, o produto depende de confiança: um dado errado custa mais que um dado atrasado.

## Decisão

1. O trabalho segue um fluxo contínuo de itens pequenos, em um quadro com limite de dois itens em andamento.
2. O projeto tem sete fases em ordem (0 a 6). Cada fase só termina quando passa um **portão verificável**, descrito no README.
3. Não há datas no roadmap. O roadmap público mostra fases e portões.
4. A fase de decisões históricas (1) vem antes do portal, do assistente e dos alertas, porque tudo depende de números que cheguem ao documento original.
5. Uma fase nova só começa quando o portão da anterior foi cumprido.

## Alternativas consideradas

- **Roadmap com datas:** descartado, por depender de estimativas pouco confiáveis e incentivar atalhos.
- **Construir portal e assistente em paralelo aos dados:** descartado, porque o assistente e o portal herdariam dados não verificados.

## Consequências

- O progresso é medido por evidência (testes, reconciliação, teste com pessoas), não por calendário.
- Um portão difícil pode prender o projeto por muito tempo. O sinal de alerta é um item que fica semanas em andamento sem entregar; nesse caso, corta-se o escopo (menos temas, menos fontes), não o portão.
- Com mais pessoas o fluxo acelera, e a ordem das fases continua valendo.
