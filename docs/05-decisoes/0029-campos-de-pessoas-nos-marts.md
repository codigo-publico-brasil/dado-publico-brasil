# ADR 0029: campos de pessoas que entram no raw e nos marts

- **Status:** proposto (2026-10-26); aprovado pelo fundador na conversa de 26/10/2026
- **Data:** 2026-10-26
- **Altera:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md), itens 2 (o nome social nunca entra no raw) e 6 (e-mail, telefone e endereço do gabinete do Senado não são lidos). Os demais itens do 0013 continuam valendo. Responde à issue #96 e à decisão de #13.

## Contexto

O raw só captura as colunas listadas em `sources/*.yml`, e os marts de pessoas expõem pouco do que Câmara, Senado e TSE publicam como dado aberto (levantamento na issue #96). Quem consulta a ficha de um eleito espera formação, ocupação, nome social e contato institucional.

## Decisão

1. **Entram**, com fonte e data de captura como todo dado:
   - **TSE (candidaturas):** nome social, grau de instrução, estado civil, ocupação, UF de nascimento, coligação e federação.
   - **Câmara (detalhe do deputado):** escolaridade, nome eleitoral, situação, condição eleitoral, partido e UF do último status e o gabinete (prédio, sala, telefone e e-mail institucional).
   - **Senado (detalhe do senador):** partido, UF, páginas oficiais, UF de naturalidade, e-mail, telefones e endereço do gabinete.
2. **Dado pessoal sinalizado.** Nome social, estado civil e grau de instrução levam `meta: pii` e a base legal é registrada no documento de LGPD (#38). São dados declarados pelo candidato e publicados pelo TSE.
3. **Continuam fora, sempre:** CPF, título de eleitor e o e-mail do candidato (`DS_EMAIL`) no TSE, e o CPF da Câmara. **Cor ou raça fica de fora** (decisão do fundador de 26/10/2026, para não acrescentar dado sensível). Certidões criminais seguem fora até decisão explícita.
4. **Sem inferência.** Campo vazio na fonte fica vazio; nenhum campo serve de base para ranking ou nota.
5. **Layouts por ano.** Os arquivos do TSE mudam de colunas entre eleições; as colunas novas são opcionais e a checagem de cabeçalho tolera a ausência (#86).

## Alternativas consideradas

- **Incluir cor ou raça:** é dado sensível pela LGPD (art. 5º, II) e exigiria base legal própria; o fundador preferiu não incluir.

## Consequências

- O raw guarda mais dado pessoal declarado, publicado pelo TSE; a exposição fica sinalizada e documentada.
- Mudar `columns` exige recarga das tabelas afetadas (#68).
- A LGPD (#38) precisa listar estas colunas.
