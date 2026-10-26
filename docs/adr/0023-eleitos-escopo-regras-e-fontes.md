# ADR 0023: Eleitos das eleições gerais: escopo, regras e fontes

- **Status:** aceito (2026-10-25, pelo fundador)
- **Data:** 2026-10-25
- **Complementa:** o [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (ligação de pessoas) e o [ADR 0016](0016-bens-votos-e-emendas.md) (bens e votos).

## Contexto

As páginas "Eleitos do seu estado" precisam, para cada eleito das eleições gerais, do resultado, da campanha e da relação com quem já exerce mandato. Os marts só expunham quem já era pessoa do projeto, o que deixaria de fora os novatos (178 dos 513 deputados federais de 2026 estavam sem vínculo). A página do TSE com a documentação dos arquivos de divulgação de resultados em JSON está atrás de uma proteção anti-robô (403) e não foi contornada.

## Decisão

1. **Fonte:** os arquivos abertos do TSE (CSV, licença CC BY, documentados): candidaturas, bens, vagas, prestação de contas e votação por município e zona. Não é ao vivo: cada captura é um instantâneo com data e hash no landing. O JSON de divulgação em tempo real fica para depois, se a documentação for obtida.
2. **Escopo:** todos os cargos em que se vota, nas eleições gerais e nas municipais: presidente, governador, senador, deputado federal, estadual e distrital, prefeito e vereador. Vale desde 1996 (a eleição de 1994 tem outro nome de arquivo e fica de fora). Eleições suplementares, vices e suplentes ficam de fora (issue 64). Novato, reeleito e retorno só existem para deputado federal e senador, os cargos com base de mandatos; a coluna fica vazia nos demais. A unidade eleitoral (`ue`, `ue_nome`) distingue o município do estado.
3. **Três marts:** `eleitos` (uma linha por eleito, inclusive quem ainda não é pessoa do projeto), `eleitos_cargos` (vagas, eleitos e pendentes por cargo e unidade) e `eleitos_campanhas` (totais de bens, receitas e despesas). Quem ainda não é pessoa do projeto aparece em `eleitos` sem criar pessoa em `identity`.
4. **Estado real, sem palpite:** `eleitos_cargos.status` é `eleito_provisorio` quando todas as vagas têm eleito pelo resultado do TSE e `aguardando_resultado` quando falta eleito. Diplomação e pendência judicial não são derivadas: o CSV não as traz e nada é inferido.
5. **Vínculo ao Congresso:** a regra do ADR 0013, mais a fila de revisão `eleitos_com_possivel_vinculo` (eleito sem vínculo com alguém de mesma data de nascimento na base), resolvida por aprovação à mão em `vinculos_aprovados`. `tipo_mandato` (reeleito, retorno ou novato) só existe para deputado federal e senador e compara com os mandatos da mesma casa pela legislatura em curso na eleição; o eleito sem vínculo fica sem `tipo_mandato`: sem prova do histórico, nada é afirmado, nem novato nem reeleito (na comparação com o Nexo, 6 deputados eleitos em 2022 saíam como novatos por falta de ligação). Novato só aparece para quem está ligado a uma pessoa e não tinha mandato na casa.
6. **Votos:** o percentual é sobre os votos nominais válidos do cargo na unidade eleitoral (sem votos de legenda) e fica vazio enquanto a votação por município e zona do ano não for carregada.
7. **Campanha:** só totais; o nome e o documento de quem doou ou forneceu não entram no raw. O total fica vazio, e não zero, quando o arquivo ainda não foi carregado. A prestação de contas é pesada (o arquivo de 2022 descompactado passa de 1,7 GB): carga só por ano e quando pedida; enquanto isso as tabelas de staging ficam vazias (macro `raw_or_empty`).
8. **Turno final:** quando o TSE marca "eleito" em mais de um turno para o mesmo candidato, vale o turno final.

## Consequências

- Cada vez que o TSE atualizar os arquivos, o resultado muda na próxima captura; a página mostra a data da captura.
- A fila de revisão de vínculos é uma lista de avisos (gap test), e não um sistema de revisão separado.
- Os dois datasets de prestação leem o mesmo pacote; o landing guarda uma cópia por dataset (distintos pela URL com fragmento).
- O arquivo de vagas de 2022 traz a eleição suplementar de governador de Roraima: a chave inclui o código da eleição e o mart filtra as suplementares pela descrição da eleição (as municipais de 2024 trazem eleições suplementares de 2025 no mesmo arquivo).
