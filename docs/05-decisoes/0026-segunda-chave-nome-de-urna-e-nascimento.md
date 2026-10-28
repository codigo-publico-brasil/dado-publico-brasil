# ADR 0026: segunda chave de ligação, nome de urna e data de nascimento

- **Status:** proposto (2026-10-26); aprovado pelo fundador na conversa de 26/10/2026
- **Data:** 2026-10-26
- **Complementa:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (ligação com a Câmara e o Senado) e [ADR 0025](0025-historico-do-eleito-ligacao-entre-eleicoes-do-tse.md) (histórico do eleito). Não troca a regra de base: acrescenta uma chave.

## Contexto

A regra do ADR 0013 compara o nome civil. O TSE mantém o nome civil de cada eleição, e ele muda: o registro de uma mesma pessoa pode trazer um nome civil em 2016, outro em 2020 e 2022 e outro em 2026. A ficha de uma deputada saiu sem foto, mandatos e histórico, embora ela esteja na Câmara com o mesmo nascimento e o mesmo nome parlamentar. Na comparação com o Nexo, 4 dos 6 deputados que saíam sem selo tinham a mesma causa.

## Decisão

1. **Segunda chave: nome de urna mais data de nascimento.** Vale nos dois lugares em que o ADR 0013 e o ADR 0025 ligam pessoas:
   - **TSE com Câmara e Senado:** o nome de urna da candidatura é igual ao nome parlamentar do deputado ou senador e a data de nascimento é a mesma. Só liga a candidatura que a regra de base não ligou, com o método `nome de urna e data de nascimento iguais e únicos` registrado em `identity`.
   - **Entre eleições do TSE:** duas candidaturas que partilham o nome civil ou o nome de urna, com a mesma data de nascimento, são da mesma pessoa, e a ligação se propaga (A liga com B por uma chave, B com C pela outra).
2. **Mesmos limites da regra de base.** Cada chave só vale quando é única: dentro de cada fonte (Câmara, Senado) só um registro tem o par, e em cada eleição só uma candidatura tem o par; homônimos não ligam. Datas de 1º de janeiro ficam de fora.
3. **Duas travas a mais para o nome de urna entre eleições.** A chave inclui a UF (quem muda de nome civil e de estado ao mesmo tempo não liga, e isso corta a maior parte dos homônimos). E uma pessoa não tem duas candidaturas na mesma eleição: o grupo em que isso acontece juntou pessoas diferentes e é descartado inteiro. Na primeira versão, 2.741 de 2,2 milhões de grupos (0,1%) tinham esse conflito (por exemplo, dois Raimundo Nonato nascidos no mesmo dia, em estados diferentes); um teste de reconciliação garante que não sobre nenhum.
4. **Cuidado com o nome de urna.** Ele é escolhido pelo candidato e pode ser genérico. Por isso exige a data de nascimento exata e a unicidade em cada eleição, e a ligação por esta chave aparece com um método próprio, auditável e separado da regra de base.

## Alternativas consideradas

- **Só a regra de base:** deixa quem mudou de nome sem ficha completa e, pior, sem selo nem foto.
- **Ligar por CPF:** liga exato, mas coloca documento pessoal no raw (a minimização do ADR 0013 o exclui).
- **Só vínculo manual (`vinculos_aprovados`):** seguro, mas não escala para os casos que vão aparecer a cada eleição.

## Consequências

- O risco novo é ligar duas pessoas diferentes com o mesmo nome de urna e a mesma data de nascimento exata. A exigência de unicidade o reduz, e o método fica visível na ligação. A conferência com uma fonte independente (o Nexo) é parte do teste de lacunas.
- Mudança de nome civil e de nome de urna ao mesmo tempo, entre duas eleições, ainda impede a ligação; a ficha diz que o histórico não está confirmado, nunca que a pessoa é novata.
