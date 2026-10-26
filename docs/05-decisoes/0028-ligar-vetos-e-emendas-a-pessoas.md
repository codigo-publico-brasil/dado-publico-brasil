# ADR 0028: ligar os votos dos vetos e as emendas parlamentares a pessoas

- **Status:** proposto (2026-10-26); depende de aprovação do fundador
- **Data:** 2026-10-26
- **Complementa:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (regra de base), [ADR 0015](0015-normas-vetos-e-constituicao.md) e [ADR 0016](0016-bens-votos-e-emendas.md), que deixaram vetos e emendas sem ligação. Responde às issues #15 e #16.

## Contexto

Dois conjuntos ficam fora de `marts.pessoas`:

- **Votos nominais dos vetos** (`vetos_votos`): a fonte traz só nome parlamentar, partido, UF e casa.
- **Emendas parlamentares** (`emendas`): a fonte traz o nome do autor e um código orçamentário (`cd_autor`), que não é o código do parlamentar. 15.962 de 94.739 emendas vêm sem autor.

A regra do projeto é nunca ligar só por nome. Mas nome mais outros atributos oficiais da própria fonte, medidos e únicos, é o mesmo tipo de evidência dos ADRs 0013 e 0026. Medi no warehouse de 26/10/2026 o que cada chave liga.

## Decisão

Uma regra para as duas fontes: **liga quando a chave inteira aponta para exatamente uma pessoa; zero ou mais de uma, não liga.** Cada vínculo grava o método e a data. O ambíguo e o sem correspondência ficam sem ligação e são medidos.

1. **Votos de vetos.** Chave: nome parlamentar (sem acento, em minúsculas) **mais UF mais casa**, comparada com o nome parlamentar ou o nome civil de quem tem **mandato na legislatura da sessão** (`marts.mandatos`). Medição na 57ª legislatura: dos 894 pares distintos, **886 ligam a uma só pessoa, 0 são ambíguos e 8 não ligam** (grafias diferentes, como "Professora Dorinha Seabra"). Os 8 seguem para a curadoria manual (`vinculos_aprovados`).
2. **Emendas.** A chave de ligação é o `cd_autor`, que a fonte usa de forma estável ao longo dos anos. Vira uma tabela de correspondência `cd_autor` para `id_pessoa`:
   - **Automática** quando o nome do autor, sem acento, é igual ao nome parlamentar ou civil de **uma só** pessoa que tinha mandato no ano da emenda;
   - **Manual** (seed aprovado por pessoa, com evidência) para os demais.
   Medição só pelo nome, sem a trava do mandato no ano: dos 1.573 `cd_autor`, 1.400 têm uma só pessoa com o nome, 58 têm duas ou mais e 35 nenhuma. A trava do mandato no ano deve reduzir os ambíguos; o número final é medido na implementação.
3. **Fica sem autor o que a fonte não atribui a uma pessoa:** emenda de relator, de bancada e de comissão, e as emendas sem `cd_autor`. A plataforma não infere nem completa.
4. **Testes:** (a) nenhum voto ou emenda liga a mais de uma pessoa; (b) um `cd_autor` com dois nomes na fonte não liga sozinho; (c) as contagens ligadas, ambíguas e sem correspondência aparecem no `coverage`.

## Alternativas consideradas

- **Ligar só por nome:** contraria a regra do projeto e erraria com homônimos.
- **Esperar um identificador oficial:** nenhuma das duas fontes o traz; o conjunto ficaria sem ligação indefinidamente.
- **Tudo manual:** seguro, mas são centenas de nomes por legislatura.

## Consequências

- Votos de vetos e emendas passam a ter ficha de autor e de votante quando a evidência é inequívoca; o resto continua visível como "sem vínculo".
- O risco novo é um nome igual, na mesma UF e casa e com mandato no mesmo período; a exigência de unicidade o reduz, e o método fica visível e auditável.
- Quem mudar de nome parlamentar entre sessões precisa do vínculo manual.
