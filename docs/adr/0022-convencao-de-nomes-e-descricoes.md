# ADR 0022: Convenção de nomes e descrições

- **Status:** aceito (2026-10-25, pelo fundador)
- **Data:** 2026-10-25

## Contexto

Os nomes de tabelas e colunas dos marts não têm padrão: `autorias` não diz autoria de quê; os identificadores misturam `id_pessoa` e `norma_id`; as datas misturam `_em`, `inicio`, `data` e `data_nascimento`; os booleanos misturam `possui_`, `tem_`, `contem_` e nenhum prefixo. Além disso, o `publish` não copia as descrições para o Postgres (0 de 32 tabelas e 0 de 365 colunas com comentário) e as camadas abaixo dos marts quase não descrevem colunas.

## Decisão

1. **Tabelas:** tema na frente, detalhe depois, sem conectivos (`proposicoes_autorias`).
2. **Colunas:** o prefixo mostra o tipo: `id_` (identificador), `dt_` (data) e `fl_` (flag), sem duplicar o tipo no nome e sem encurtar o nome (`dt_nascimento`, `fl_votacao_secreta`).
3. **Raw espelha a fonte** nos nomes, mas também é descrito.
4. **Toda tabela e coluna, em todas as camadas, tem descrição**, e o `publish` a leva ao Postgres.
5. **Auditabilidade:** nenhuma regra de nome ou transformação pode esconder a origem da informação.
6. **Garantia:** a convenção fica em [documento próprio](../engenharia/convencao-de-nomes.md), citado no `CLAUDE.md`, no `AGENTS.md` e no modelo de PR, com teste no CI.
7. **Os marts são renomeados** conforme [`renomeacao-dos-marts.md`](../dados/renomeacao-dos-marts.md); o staging e o intermediate seguem a mesma regra.

## Alternativas consideradas

- **Conectivos nos nomes (`autorias_de_proposicoes`):** mais legíveis em frase, mas separam tabelas parecidas na ordenação.
- **Sufixo de tipo (`pessoa_id`):** é o padrão atual de parte das colunas; o fundador preferiu o prefixo, que deixa o tipo visível em ordem alfabética.
- **Gerar um de-para automático de colunas a partir do SQL:** viável, mas rejeitado por ora.

## Consequências

- Os marts mudam de contrato: 13 tabelas e 101 colunas são renomeadas, e a aplicação quem-decidiu precisa mudar junto (PR coordenado).
- Códigos que a fonte usa (`emenda_codigo`, `autor_codigo`...) ainda não têm prefixo definido; a decisão fica registrada no anexo de renomeação.
