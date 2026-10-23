# ADR 0016: Bens, votos por candidato e emendas parlamentares (escopo e privacidade)

- **Status:** aceito (2026-10-23, pelo fundador)
- **Data:** 2026-10-23
- **Complementa:** o [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (TSE e ligação de pessoas) e o [ADR 0015](0015-normas-vetos-e-constituicao.md).

## Contexto

A pesquisa de fonte de 23/10/2026 achou, no TSE, os bens declarados e os votos por candidato (CC BY) e, no Portal da Transparência, as emendas parlamentares em arquivo único sem token. O DOU tem licença sem derivações e o TCU não tem licença aberta (ver o [catálogo de fontes](../dados/fontes-de-dados.md)).

## Decisão

1. **TSE: bens e votos de todos os cargos no raw.** `bens` (2006 em diante, `step: 4`) e `votacao` (por município e zona, 1998 em diante) não filtram o cargo: a plataforma guarda o que a fonte publica, no staging. O nome social não entra. Os votos pesam (9,38 milhões de linhas em 2022): a carga é por ano, com `--years ANO --dataset votacao`, e a carga de todas as eleições (2,4 GB compactados) só quando pedida.
2. **Os marts só expõem quem é pessoa do projeto** (como no ADR 0013): `bens_de_candidatos` e `votos_de_candidatos` ligam-se a `marts.candidaturas` pela chave que o TSE já traz (`SQ_CANDIDATO`), sem regra nova de identidade. Votos por município e zona, e bens de candidatos que não são pessoa do projeto, ficam no staging.
3. **Layouts antigos por declaração.** `aliases` no dataset diz o nome antigo de cada coluna que mudou de nome (os arquivos de bens de 2006 e 2010 usam `NR_ORDEM_CANDIDATO` e `DT_ULTIMA_ATUALIZACAO`), sem código próprio.
4. **Emendas do Portal da Transparência**, em fonte própria `executivo/federal/transparencia`, com os três datasets lendo o mesmo zip (distintos por fragmento na URL, `#emendas`, `#convenios`, `#favorecidos`, que não vai ao servidor): emendas, convênios e favorecidos.
5. **Favorecido pessoa física nunca entra.** São 181 mil cidadãos comuns, com nome e CPF mascarado. Só pessoa jurídica (CNPJ) e unidade gestora; um teste barra qualquer outro tipo ou código mascarado nos marts.
6. **A emenda não é ligada a `pessoas`.** O autor vem pelo nome e por um código orçamentário que não é o do parlamentar; a regra do ADR 0013 não liga só por nome. Expõe-se o autor como a fonte publica, com caixa padronizada.
7. **`--dataset` limita a extração** a um dataset anual, único ou por item, para pedir os pesados sem baixar os demais.
8. **Não entram agora:** DOU (licença CC BY-ND e sem credencial: decisão do fundador pendente) e TCU (sem licença aberta).

## Alternativas consideradas

- **Filtrar os votos só ao Congresso na leitura:** reduziria de 9,4 milhões para 3,8 milhões de linhas em 2022; o fundador preferiu guardar tudo.
- **Ligar a emenda ao parlamentar por nome:** possível, mas é regra nova de identidade e contraria o ADR 0013.
- **Carregar o favorecido pessoa física com o CPF mascarado:** o nome e os dígitos visíveis ainda identificam cidadãos comuns, que não são agentes públicos.

## Consequências

- O raw cresce com os votos: cerca de 9,4 milhões de linhas por eleição carregada.
- As emendas ficam sem ligação a `pessoas`; o relatório de lacunas registra isso.
- Se o Portal da Transparência mudar o layout do arquivo, o contrato `columns` denuncia na carga (colunas faltantes viram vazias e os testes de conversão medem valores que não viram número).
