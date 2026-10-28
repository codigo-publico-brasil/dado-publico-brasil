# Visão geral

Para quem chega ao projeto. Responde: o que é, para quê, até onde vai e o que nunca pode violar.

## O que é

A **camada de dados** do [Código Público Brasil](https://github.com/codigo-publico-brasil): captura dados abertos do poder público, organiza em camadas e os entrega prontos, com fonte oficial, URL e data de captura, para qualquer aplicação consumir. A camada é genérica, sem acoplamento a nenhuma aplicação (a fronteira é o esquema `marts`/`servico`); aplicações como o [No Cargo](https://github.com/codigo-publico-brasil/nocargo) e o [quem-decidiu](https://github.com/codigo-publico-brasil/quem-decidiu) são consumidoras.

## Escopo

- Qualquer poder (legislativo, executivo, judiciário) e esfera (federal, estadual, municipal). Hoje: Câmara dos Deputados, Senado Federal, TSE (candidaturas ao Congresso), Portal da Transparência (emendas), Constituição e Diário Oficial da União (só o arquivo original).
- Código aberto (AGPL-3.0) e dados curados abertos (CC BY 4.0), a confirmar.
- Material de estudo: a documentação explica cada decisão de arquitetura e de dados.

## Regras de dados (nunca violar)

1. Todo dado carrega fonte oficial, URL e data de captura.
2. O landing (arquivo recebido) é imutável, com hash.
3. Nada é inventado, estimado ou completado: faltou, fica vazio, e a lacuna é medida por teste.
4. Nenhum documento pessoal (CPF, RG...); só dado público de agente público.
5. Sem métricas avaliativas derivadas (nota, ranking): a plataforma entrega fatos.
6. Conteúdo gerado por IA fica em tabelas próprias, rotulado com modelo e versão, nunca misturado ao dado oficial.

As regras de apresentação (neutralidade, sem recomendação de voto) pertencem às aplicações.

## Próximo passo de leitura

[`02-arquitetura.md`](02-arquitetura.md).
