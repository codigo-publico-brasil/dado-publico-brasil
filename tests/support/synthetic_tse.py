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

from dado_publico_brasil.ingestion import contract as contracts

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
            ANO_ELEICAO="2022", NR_TURNO="1", DS_CARGO=cargo, SQ_CANDIDATO=sq, NR_CANDIDATO="1234", NM_CANDIDATO=nome, SG_UE=uf,
            NM_URNA_CANDIDATO=urna, DS_SITUACAO_CANDIDATURA=situacao, SG_PARTIDO=partido, NM_PARTIDO=f"PARTIDO {partido}",
            DT_NASCIMENTO=nasc, DS_GENERO="FEMININO", DS_SIT_TOT_TURNO=resultado, SG_UF=uf,
            NR_CPF_CANDIDATO="12345678900", DS_EMAIL="x@exemplo.com", NR_TITULO_ELEITORAL_CANDIDATO="000111222333",
        )  # fmt: skip
        escritor.writerow([valores[c] for c in COLUNAS])
    return saida.getvalue().encode("latin-1")


BENS_COLUNAS = (
    "DT_GERACAO HH_GERACAO ANO_ELEICAO CD_TIPO_ELEICAO NM_TIPO_ELEICAO CD_ELEICAO DS_ELEICAO DT_ELEICAO SG_UF SG_UE "
    "NM_UE SQ_CANDIDATO NR_ORDEM_BEM_CANDIDATO CD_TIPO_BEM_CANDIDATO DS_TIPO_BEM_CANDIDATO DS_BEM_CANDIDATO "
    "VR_BEM_CANDIDATO DT_ULT_ATUAL_BEM_CANDIDATO HH_ULT_ATUAL_BEM_CANDIDATO"
).split()
#       sq, ordem, tipo, descrição, valor
BENS = [
    ("1001", "1", "Casa", "Casa na cidade", "150000,00"),
    ("1001", "2", "Veículo automotor terrestre", "Carro popular", "30000,50"),
    ("1002", "1", "Aplicação de renda fixa", "CDB", "5000,00"),
    ("1006", "1", "Terreno", "Terreno de candidato estadual", "70000,00"),  # não liga a pessoa: só no staging
]
VOTACAO_COLUNAS = (
    "DT_GERACAO HH_GERACAO ANO_ELEICAO CD_TIPO_ELEICAO NM_TIPO_ELEICAO NR_TURNO CD_ELEICAO DS_ELEICAO DT_ELEICAO "
    "TP_ABRANGENCIA SG_UF SG_UE NM_UE CD_MUNICIPIO NM_MUNICIPIO NR_ZONA CD_CARGO DS_CARGO SQ_CANDIDATO NR_CANDIDATO "
    "NM_CANDIDATO NM_URNA_CANDIDATO NM_SOCIAL_CANDIDATO DS_SITUACAO_CANDIDATURA DS_DETALHE_SITUACAO_CAND NR_PARTIDO "
    "SG_PARTIDO SG_FEDERACAO ST_VOTO_EM_TRANSITO QT_VOTOS_NOMINAIS NM_TIPO_DESTINACAO_VOTOS "
    "QT_VOTOS_NOMINAIS_VALIDOS DS_SIT_TOT_TURNO"
).split()
#         sq, cargo, uf, município, zona, nominais, válidos, destinação
VOTOS = [
    ("1001", "Deputado Federal", "RJ", "60011", "1", "1000", "1000", "Válido"),
    ("1001", "Deputado Federal", "RJ", "60011", "2", "500", "500", "Válido"),
    ("1001", "Deputado Federal", "RJ", "60012", "1", "250", "250", "Válido"),
    ("1001", "Deputado Federal", "RJ", "60012", "2", "20", "0", "Anulado"),
    ("1002", "Deputado Federal", "SP", "70011", "1", "700", "700", "Válido"),
    ("1006", "Deputado Estadual", "SP", "70011", "1", "90", "90", "Válido"),
]


UF_DE = {linha[1]: linha[7] for linha in LINHAS}  # sq -> UF do candidato


def _tabela(colunas: Sequence[str], linhas: Sequence[dict[str, str]]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writerow(colunas)
    for linha in linhas:
        valores = (
            dict.fromkeys(colunas, "#NULO#") | {"ANO_ELEICAO": "2022", "DT_GERACAO": "23/10/2026"} | linha
        )
        escritor.writerow([valores[c] for c in colunas])
    return saida.getvalue().encode("latin-1")


def _bens() -> bytes:
    return _tabela(
        BENS_COLUNAS,
        [
            {"SQ_CANDIDATO": sq, "NR_ORDEM_BEM_CANDIDATO": ordem, "DS_TIPO_BEM_CANDIDATO": tipo,
             "DS_BEM_CANDIDATO": descricao, "VR_BEM_CANDIDATO": valor, "SG_UF": UF_DE[sq], "SG_UE": UF_DE[sq],
             "DT_ULT_ATUAL_BEM_CANDIDATO": "06/09/2022"}
            for sq, ordem, tipo, descricao, valor in BENS
        ],
    )  # fmt: skip


def _votacao() -> bytes:
    nomes = {linha[1]: (linha[2], linha[3]) for linha in LINHAS}  # sq -> (nome civil, nome de urna)
    return _tabela(
        VOTACAO_COLUNAS,
        [
            {"NR_TURNO": "1", "SQ_CANDIDATO": sq, "DS_CARGO": cargo, "SG_UF": uf, "SG_UE": uf, "CD_MUNICIPIO": municipio,
             "NM_MUNICIPIO": f"MUNICIPIO {municipio}", "NR_ZONA": zona, "NM_CANDIDATO": nomes[sq][0],
             "NM_URNA_CANDIDATO": nomes[sq][1], "NM_SOCIAL_CANDIDATO": "NOME SOCIAL SIGILOSO",
             "QT_VOTOS_NOMINAIS": nominais, "QT_VOTOS_NOMINAIS_VALIDOS": validos, "NM_TIPO_DESTINACAO_VOTOS": destino,
             "ST_VOTO_EM_TRANSITO": "N", "DS_SIT_TOT_TURNO": "ELEITO POR QP"}
            for sq, cargo, uf, municipio, zona, nominais, validos, destino in VOTOS
        ],
    )  # fmt: skip


def tse_files(pasta: Path) -> dict[str, Path]:
    """Os pacotes sintéticos de 2022 (candidaturas, bens e votos), pela URL oficial."""
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
    arquivos = {contrato.url("candidaturas", 2022): destino}
    for dataset, nome, conteudo in (
        ("bens", "bem_candidato_2022", _bens()),
        ("votacao", "votacao_candidato_munzona_2022", _votacao()),
    ):
        pacote_destino = pasta / f"{nome}.zip"
        with zipfile.ZipFile(pacote_destino, "w") as pacote:
            pacote.writestr(f"{nome}_SP.csv", conteudo)  # o `_BRASIL.csv` é o único lido; este é só ruído
            pacote.writestr(f"{nome}_BRASIL.csv", conteudo)
        arquivos[contrato.url(dataset, 2022)] = pacote_destino
    return arquivos
