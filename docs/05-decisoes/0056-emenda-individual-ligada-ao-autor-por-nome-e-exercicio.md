# ADR 0056: emenda individual ligada ao autor por nome e exercício

- **Status:** aceito em 2026-11-12 (decisão do fundador); antes proposto (2026-11-11); retoma a parte das emendas do [ADR 0028](0028-ligar-vetos-e-emendas-a-pessoas.md) (defasado: nunca foi implementada). Responde à issue #16.
- **Data:** 2026-11-11
- **Complementa:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (regra de base: conservadora, único ou nada).

## Contexto

`fct_emendas` traz o autor pelo nome e pelo `cd_autor`, que é o código do SIAFI e não o do parlamentar (o código da emenda tem 12 dígitos: ano, código do autor e número da emenda do autor). A fonte não traz CPF, nascimento nem código da Câmara ou do Senado, então a regra do ADR 0013 (nome civil mais nascimento) não se aplica. Ligar só por nome erra com homônimos.

## Decisão

1. **Só emenda individual** (`tipo` começa por "Emenda Individual") com `cd_autor` e nome informados é candidata. Bancada, comissão e relator não têm um parlamentar autor; emenda sem autor segue sem autor.
2. **Liga quando o nome inteiro aponta para uma só pessoa.** O nome do autor (sem acento, minúsculas, espaços únicos) é comparado ao nome público e ao nome civil de `dim_pessoas`; só conta quem **exerceu mandato federal** (`fct_exercicios`) no ano da emenda ou no anterior (a emenda é proposta no ano anterior ao do orçamento). Zero ou mais de uma pessoa: não liga.
3. **Código com dois nomes não liga.** Se o mesmo `cd_autor` aparece com mais de um nome na fonte (em qualquer ano), nenhuma de suas emendas liga.
4. **Registro por linha.** `fct_emendas` ganha `id_pessoa`, `regra_ligacao_pessoa` (`nome_parlamentar_e_exercicio` ou `nome_civil_e_exercicio`) e `precisao_ligacao_pessoa` (`derivada`: inferida por regra, sem identificador oficial). Sem vínculo, as três ficam vazias; nada é completado.
5. **Medida e teste.** `emendas_individuais_sem_pessoa` (aviso) conta o que ficou sem ligar; o teste `emendas_ligadas_a_mais_de_uma_pessoa_ou_fora_da_regra` barra vínculo que a regra não permite.
6. **Fora desta entrega:** correspondência manual (seed por `cd_autor`, com evidência) para os homônimos e os nomes diferentes; vira issue quando a medida real mostrar o tamanho.

## Alternativas consideradas

- **Ligar só por nome:** contraria a regra do projeto.
- **Tabela de correspondência `cd_autor` para pessoa:** o `cd_autor` é estável, mas o vínculo por ano mantém a trava do mandato e evita uma tabela a mais; o seed manual do item 6 ainda pode usá-lo.
- **Esperar um identificador oficial:** a fonte não o traz; ficaria sem ligação indefinidamente.

## Consequências

- Emendas individuais passam a ter ficha de autor quando a evidência é inequívoca; o resto continua visível como sem vínculo.
- Risco: homônimo que a regra não vê (ex.: dois mandatos do mesmo nome em períodos diferentes dentro da janela é ambíguo e não liga; um homônimo sem mandato federal nunca entra). Quem mudou de nome parlamentar fica sem vínculo.
