# ADR 0057: voto nominal de veto ligado à pessoa por nome, UF e exercício

- **Status:** proposto (2026-11-12); retoma a parte dos vetos do [ADR 0028](0028-ligar-vetos-e-emendas-a-pessoas.md) (defasado: nunca foi implementada). Responde à issue #15. Irmão do ADR 0056 (emenda individual ligada ao autor), que faz o mesmo para emendas.
- **Data:** 2026-11-12
- **Complementa:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (regra conservadora: único ou nada).

## Contexto

`fct_vetos_votos` traz, por voto, só nome do parlamentar, partido, UF e casa. A fonte não traz código nem nascimento, então a regra do ADR 0013 não se aplica; ligar só por nome erra com homônimos.

## Decisão

1. **Liga quando a chave inteira aponta para exatamente uma pessoa.** O nome do voto (sem acento, minúsculas, espaços únicos) é comparado ao nome público e ao nome civil de `dim_pessoas`; só conta quem tinha **exercício** (`fct_exercicios`) do cargo da casa (Câmara: deputado federal; Senado: senador), **na mesma UF** e **no dia da sessão** do dispositivo (`dt_sessao`). Zero ou mais de uma pessoa: não liga.
2. **Registro por linha.** `fct_vetos_votos` ganha `id_pessoa`, `regra_ligacao_pessoa` (`nome_parlamentar_e_exercicio` ou `nome_civil_e_exercicio`) e `precisao_ligacao_pessoa` (`derivada`: inferida por regra, sem identificador oficial). Sem vínculo, as três ficam vazias; nada é completado.
3. **Medida e teste.** `vetos_votos_sem_pessoa` (aviso) conta o que ficou sem ligar; `votos_de_veto_ligados_a_mais_de_uma_pessoa` barra vínculo ambíguo.
4. **Fora desta entrega:** curadoria manual (`vinculos_aprovados`) para grafias diferentes; vira issue quando a medida real mostrar o tamanho.

## Alternativas consideradas

- **Ligar só por nome:** contraria a regra do projeto.
- **Trava por legislatura em vez de dia:** mais fraca; quem assumiu como suplente no meio da legislatura entraria como candidato indevido.
- **Esperar um código oficial:** a fonte não o traz.

## Consequências

- Votos de veto ganham ficha do votante quando a evidência é inequívoca; o resto continua visível como sem vínculo.
- Risco: homônimo na mesma casa, UF e dia não liga (conservador); quem mudou de nome parlamentar fica sem vínculo. A dependência de `fct_exercicios` herda as lacunas dele.
