"""Dados sintéticos do TSE (pacote .zip em latin-1, como o real); sem rede.

O pacote tem os CSVs por UF, o `_BRASIL.csv` que reúne todos (o único lido) e um PDF. O arquivo traz CPF, título
de eleitor e e-mail de propósito: a plataforma não os lê. As candidaturas montam os casos da regra de ligação
(nome civil e nascimento iguais e únicos):

- BIA SOUZA (01/01/1990): deputada federal eleita; é a deputada 11 da Câmara e a senadora 5003 do Senado (mesma pessoa);
- ANA DA SILVA (03/02/1980): deputada federal não eleita; liga-se à deputada 10;
- ROBERTO BARREIRAS (05/05/1970): duas candidaturas ao Senado no mesmo ano com o mesmo nome e nascimento: ambígua, não liga;
- CARLOS ELEITO: eleito a deputado federal e sem correspondente: fica sem vínculo (lacuna medida);
- FULANO ESTADUAL: deputado estadual, fora do que a declaração deixa passar.
"""

import csv
import io
import zipfile
from collections.abc import Sequence
from pathlib import Path

from plataforma_dados.ingestion import contract as contracts

COLUNAS = (
    "DT_GERACAO HH_GERACAO ANO_ELEICAO CD_TIPO_ELEICAO NM_TIPO_ELEICAO NR_TURNO CD_ELEICAO DS_ELEICAO DT_ELEICAO "
    "TP_ABRANGENCIA SG_UF SG_UE NM_UE CD_CARGO DS_CARGO SQ_CANDIDATO NR_CANDIDATO NM_CANDIDATO NM_URNA_CANDIDATO "
    "NM_SOCIAL_CANDIDATO NR_CPF_CANDIDATO DS_EMAIL CD_SITUACAO_CANDIDATURA DS_SITUACAO_CANDIDATURA TP_AGREMIACAO "
    "NR_PARTIDO SG_PARTIDO NM_PARTIDO SG_UF_NASCIMENTO DT_NASCIMENTO NR_TITULO_ELEITORAL_CANDIDATO CD_GENERO "
    "DS_GENERO CD_GRAU_INSTRUCAO DS_GRAU_INSTRUCAO CD_SIT_TOT_TURNO DS_SIT_TOT_TURNO"
).split()

#       cargo, sq, nome civil, nome de urna, nascimento, situação, resultado, uf, partido
LINHAS = [
    (
        "DEPUTADO FEDERAL",
        "1001",
        "BIA SOUZA",
        "BIA DO POVO",
        "01/01/1990",
        "DEFERIDO",
        "ELEITO POR QP",
        "RJ",
        "BBB",
    ),
    (
        "DEPUTADO FEDERAL",
        "1002",
        "ANA DA SILVA",
        "ANA SILVA",
        "03/02/1980",
        "DEFERIDO",
        "NÃO ELEITO",
        "SP",
        "AAA",
    ),
    ("SENADOR", "1003", "ROBERTO BARREIRAS", "BETO", "05/05/1970", "DEFERIDO", "NÃO ELEITO", "SP", "AAA"),
    ("SENADOR", "1004", "ROBERTO BARREIRAS", "BETO B", "05/05/1970", "DEFERIDO", "NÃO ELEITO", "SP", "CCC"),
    (
        "DEPUTADO FEDERAL",
        "1005",
        "CARLOS ELEITO",
        "CARLOS",
        "09/09/1969",
        "DEFERIDO",
        "ELEITO POR MÉDIA",
        "MG",
        "CCC",
    ),
    (
        "DEPUTADO ESTADUAL",
        "1006",
        "FULANO ESTADUAL",
        "FULANO",
        "10/10/1970",
        "DEFERIDO",
        "ELEITO POR QP",
        "SP",
        "AAA",
    ),
]


def _csv(linhas: Sequence[tuple[str, ...]]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writerow(COLUNAS)
    for cargo, sq, nome, urna, nasc, situacao, resultado, uf, partido in linhas:
        valores = dict.fromkeys(COLUNAS, "#NULO#")
        valores.update(
            ANO_ELEICAO="2022", NR_TURNO="1", DS_CARGO=cargo, SQ_CANDIDATO=sq, NR_CANDIDATO="1234", NM_CANDIDATO=nome,
            NM_URNA_CANDIDATO=urna, DS_SITUACAO_CANDIDATURA=situacao, SG_PARTIDO=partido, NM_PARTIDO=f"PARTIDO {partido}",
            DT_NASCIMENTO=nasc, DS_GENERO="FEMININO", DS_SIT_TOT_TURNO=resultado, SG_UF=uf,
            NR_CPF_CANDIDATO="12345678900", DS_EMAIL="x@exemplo.com", NR_TITULO_ELEITORAL_CANDIDATO="000111222333",
        )  # fmt: skip
        escritor.writerow([valores[c] for c in COLUNAS])
    return saida.getvalue().encode("latin-1")


def tse_files(pasta: Path) -> dict[str, Path]:
    """O pacote sintético de 2022, pela URL oficial."""
    pasta.mkdir(parents=True, exist_ok=True)
    contrato = contracts.find("tse")
    destino = pasta / "consulta_cand_2022.zip"
    sentinela = (
        "DEPUTADO FEDERAL",
        "9999",
        "SENTINELA SO NO ESTADO",
        "S",
        "01/01/1950",
        "DEFERIDO",
        "NÃO ELEITO",
        "SP",
        "AAA",
    )
    with zipfile.ZipFile(destino, "w") as pacote:
        pacote.writestr("leiame.pdf", b"%PDF-1.4 sintetico")
        pacote.writestr(
            "consulta_cand_2022_SP.csv", _csv([*LINHAS[:2], sentinela])
        )  # só o _BRASIL.csv é lido
        pacote.writestr("consulta_cand_2022_BRASIL.csv", _csv(LINHAS))
    return {contrato.url("candidaturas", 2022): destino}
