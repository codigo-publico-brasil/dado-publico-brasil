"""Dados sintéticos do TSE (pacote .zip em latin-1, como o real); sem rede.

O pacote tem os CSVs por UF, o `_BRASIL.csv` que reúne todos (o único lido) e um PDF. O arquivo traz CPF, título
de eleitor e e-mail de propósito: a plataforma não os lê. As candidaturas montam os casos da regra de ligação
(nome civil e nascimento iguais e únicos):

- BIA SOUZA (01/01/1990): deputada federal eleita; é a deputada 11 da Câmara e a senadora 5003 do Senado (mesma pessoa);
- ANA DA SILVA (03/02/1980): deputada federal não eleita; liga-se à deputada 10;
- ROBERTO BARREIRAS (05/05/1970): duas candidaturas ao Senado no mesmo ano com o mesmo nome e nascimento: ambígua, não liga;
- CARLOS ELEITO: eleito a deputado federal e sem correspondente: fica sem vínculo (lacuna medida);
- FULANO ESTADUAL: deputado estadual eleito em SP;
- MUNICIPAIS: prefeito e vereadores do município 60011 (eleitos e não eleito) e um prefeito de eleição suplementar,
  que não entra em `marts.fct_mandatos`.
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
    "DS_GENERO CD_GRAU_INSTRUCAO DS_GRAU_INSTRUCAO DS_ESTADO_CIVIL DS_OCUPACAO NM_COLIGACAO DS_COMPOSICAO_COLIGACAO "
    "SG_FEDERACAO DS_COMPOSICAO_FEDERACAO CD_SIT_TOT_TURNO DS_SIT_TOT_TURNO"
).split()

#       cargo, sq, nome civil, nome de urna, nascimento, situação, resultado, uf, partido
LINHAS = [
    ("GOVERNADOR", "3001", "GOVERNO REELEITO", "GOV", "02/03/1960", "DEFERIDO", "ELEITO", "SP", "AAA"),
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


#               cargo, sq, nome civil, nome de urna, resultado, eleição (CD_ELEICAO, DS_ELEICAO)
MUNICIPAIS = [
    ("PREFEITO", "1010", "PREFEITO ELEITO", "PREFEITO", "ELEITO", ("700", "Eleições Ordinárias 2022")),
    ("VEREADOR", "1011", "VEREADORA UM", "VEREADORA", "ELEITO POR QP", ("700", "Eleições Ordinárias 2022")),
    (
        "VEREADOR",
        "1012",
        "VEREADOR DOIS",
        "VEREADOR",
        "ELEITO POR MÉDIA",
        ("700", "Eleições Ordinárias 2022"),
    ),
    ("VEREADOR", "1013", "VEREADOR TRES", "TRES", "NÃO ELEITO", ("700", "Eleições Ordinárias 2022")),
    (
        "VEREADOR",
        "1015",
        "VEREADOR MEDIA",
        "MEDIA",
        "MÉDIA",
        ("700", "Eleições Ordinárias 2022"),
    ),  # nome antigo de eleito por média
    (
        "PREFEITO",
        "1014",
        "PREFEITO SUPLEMENTAR",
        "SUPLEMENTAR",
        "ELEITO",
        ("701", "Eleição Suplementar Teste 2023"),
    ),
    (  # renovada: a descrição não diz "suplementar", só o código de eleição a distingue (issue 74)
        "PREFEITO",
        "1016",
        "PREFEITO RENOVADA",
        "RENOVADA",
        "ELEITO",
        ("702", "Nova Eleição Teste 2013"),
    ),
]


def _municipais() -> list[dict[str, str]]:
    return [
        {"ANO_ELEICAO": "2022", "NR_TURNO": "1", "DS_CARGO": cargo, "SQ_CANDIDATO": sq, "NM_CANDIDATO": nome,
         "NM_URNA_CANDIDATO": urna, "DS_SIT_TOT_TURNO": resultado, "CD_ELEICAO": eleicao[0], "DS_ELEICAO": eleicao[1],
         "SG_UF": "RJ", "SG_UE": "60011", "NM_UE": "MUNICIPIO 60011", "DS_SITUACAO_CANDIDATURA": "DEFERIDO",
         "SG_PARTIDO": "AAA", "NM_PARTIDO": "PARTIDO AAA", "DT_NASCIMENTO": "02/02/1975", "DS_GENERO": "MASCULINO",
         "NR_CANDIDATO": "12345", "DT_ELEICAO": "02/10/2022"}
        for cargo, sq, nome, urna, resultado, eleicao in MUNICIPAIS
    ]  # fmt: skip


# A eleição anterior (2018): Carlos foi eleito (reeleito em 2022 pela prova do TSE) e Fulano não foi eleito.
LINHAS_2018 = [
    # governador eleito em 2018 e de novo em 2022 (mesmo nome civil e nascimento): reeleito pela prova do TSE
    ("GOVERNADOR", "2010", "GOVERNO REELEITO", "GOV", "02/03/1960", "DEFERIDO", "ELEITO", "SP", "AAA"),
    (
        "DEPUTADO FEDERAL",
        "2005",
        "CARLOS ELEITO",
        "CARLOS",
        "09/09/1969",
        "DEFERIDO",
        "ELEITO POR QP",
        "MG",
        "CCC",
    ),
    (
        "DEPUTADO ESTADUAL",
        "2006",
        "FULANO ESTADUAL",
        "FULANO",
        "10/10/1970",
        "DEFERIDO",
        "NÃO ELEITO",
        "SP",
        "AAA",
    ),
    # Ana mudou de nome civil entre as eleições: o nome de urna e o nascimento a ligam (ADR 0026)
    (
        "DEPUTADO FEDERAL",
        "2007",
        "ANA CLARA DA SILVA",
        "ANA ÁRVORE",
        "03/02/1980",
        "DEFERIDO",
        "NÃO ELEITO",
        "SP",
        "AAA",
    ),
    (
        "DEPUTADO FEDERAL",
        "2008",
        "ANA MARIA SILVA",
        "ANA SILVA",
        "03/02/1980",
        "DEFERIDO",
        "NÃO ELEITO",
        "SP",
        "AAA",
    ),
]


def _csv(linhas: Sequence[tuple[str, ...]], ano: str = "2022", municipais: bool = True) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL)
    escritor.writerow(COLUNAS)
    for extra in _municipais() if municipais else []:
        escritor.writerow([({c: "#NULO#" for c in COLUNAS} | extra)[c] for c in COLUNAS])
    for cargo, sq, nome, urna, nasc, situacao, resultado, uf, partido in linhas:
        valores = dict.fromkeys(COLUNAS, "#NULO#")
        valores.update(
            ANO_ELEICAO=ano, NR_TURNO="1", DS_CARGO=cargo, SQ_CANDIDATO=sq, NR_CANDIDATO="1234", NM_CANDIDATO=nome, SG_UE=uf,
            NM_URNA_CANDIDATO=urna, DS_SITUACAO_CANDIDATURA=situacao, SG_PARTIDO=partido, DT_ELEICAO=f"07/10/{ano}", NM_PARTIDO=f"PARTIDO {partido}",
            DT_NASCIMENTO=nasc, DS_GENERO="FEMININO", DS_SIT_TOT_TURNO=resultado, SG_UF=uf,
            NR_CPF_CANDIDATO="12345678900", DS_EMAIL="x@exemplo.com", NR_TITULO_ELEITORAL_CANDIDATO="000111222333",
            CD_CARGO=CODIGO_DO_CARGO.get(cargo.title(), "#NULO#"), NR_PARTIDO="10",
            CD_ELEICAO="544" if ano == "2022" else "#NULO#",  # o código da eleição geral, o mesmo do arquivo de vagas
        )  # fmt: skip
        if sq == "1001":  # o que o candidato declara (ADR 0029)
            valores.update(
                NM_SOCIAL_CANDIDATO="BIA SOCIAL", DS_GRAU_INSTRUCAO="SUPERIOR COMPLETO", DS_ESTADO_CIVIL="SOLTEIRO(A)",
                DS_OCUPACAO="ADVOGADO", NM_COLIGACAO="COLIGACAO TESTE", SG_FEDERACAO="FED",
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
             "NM_UE": "#NE", "NM_MUNICIPIO": f"MUNICIPIO {municipio}", "NR_ZONA": zona, "NM_CANDIDATO": nomes[sq][0],
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
    # 2018: só candidaturas têm linhas; bens, votos e vagas vêm vazios (o plano pede todos os conjuntos do ano)
    for dataset, nome, conteudo in (
        ("candidaturas", "consulta_cand_2018", _csv(LINHAS_2018, "2018", municipais=False)),
        ("bens", "bem_candidato_2018", _tabela(BENS_COLUNAS, [])),
        ("votacao", "votacao_candidato_munzona_2018", _tabela(VOTACAO_COLUNAS, [])),
        ("vagas", "consulta_vagas_2018", _tabela(VAGAS_COLUNAS, [])),
    ):
        arquivos[contrato.url(dataset, 2018)] = _pacote(
            pasta / f"{nome}.zip", {f"{nome}_BRASIL.csv": conteudo}
        )
    for dataset, nome, conteudo in (
        ("bens", "bem_candidato_2022", _bens()),
        ("votacao", "votacao_candidato_munzona_2022", _votacao()),
    ):
        pacote_destino = pasta / f"{nome}.zip"
        with zipfile.ZipFile(pacote_destino, "w") as pacote:
            pacote.writestr(f"{nome}_SP.csv", conteudo)  # o `_BRASIL.csv` é o único lido; este é só ruído
            pacote.writestr(f"{nome}_BRASIL.csv", conteudo)
        arquivos[contrato.url(dataset, 2022)] = pacote_destino
    # fotos oficiais: um pacote por UF e ano; só o do RJ em 2022 traz a foto da BIA (sq 1001), os demais não têm imagem
    for ano in (2018, 2022):
        for dataset in (d for d in contrato.datasets if d.startswith("fotos_")):
            membros = {"leiame.txt": b"sem fotos"}
            if (ano, dataset) == (2022, "fotos_rj"):
                membros = {"FRJ1001_div.jpg": FOTO}
            arquivos[contrato.url(dataset, ano)] = _pacote(pasta / f"{dataset}_{ano}.zip", membros)
    arquivos[contrato.url("vagas", 2022)] = _pacote(
        pasta / "consulta_vagas_2022.zip", {"consulta_vagas_2022_BRASIL.csv": _vagas()}
    )
    contas = _pacote(
        pasta / "prestacao_de_contas_eleitorais_candidatos_2022.zip",
        {
            "receitas_candidatos_2022_BRASIL.csv": _receitas(),
            "receitas_candidatos_doador_originario_2022_BRASIL.csv": _receitas(),  # não pode ser lido
            "despesas_contratadas_candidatos_2022_BRASIL.csv": _despesas(),
        },
    )
    arquivos[contrato.url("receitas_candidatos", 2022)] = contas
    arquivos[contrato.url("despesas_candidatos", 2022)] = contas
    # 2018 (a prestação de contas é pedida desde 2018): o mesmo pacote, sem linhas
    contas_2018 = _pacote(
        pasta / "prestacao_de_contas_eleitorais_candidatos_2018.zip",
        {
            "receitas_candidatos_2018_BRASIL.csv": _tabela(RECEITAS_COLUNAS, []),
            "despesas_contratadas_candidatos_2018_BRASIL.csv": _tabela(DESPESAS_COLUNAS, []),
        },
    )
    arquivos[contrato.url("receitas_candidatos", 2018)] = contas_2018
    arquivos[contrato.url("despesas_candidatos", 2018)] = contas_2018
    return arquivos


FOTO = (
    bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b" foto sintetica"
)  # um JPEG de mentira: só o nome do arquivo e os bytes importam


VAGAS_COLUNAS = "DT_GERACAO HH_GERACAO ANO_ELEICAO CD_TIPO_ELEICAO NM_TIPO_ELEICAO CD_ELEICAO DS_ELEICAO DT_ELEICAO DT_POSSE SG_UF SG_UE NM_UE CD_CARGO DS_CARGO QT_VAGA".split()  # noqa: E501
#       uf, cargo, vagas: RJ completa (1 de 1), MG com vaga pendente (1 de 2) e SP sem nenhum eleito
VAGAS = [
    ("RJ", "Deputado Federal", "1"),
    ("MG", "Deputado Federal", "2"),
    ("SP", "Senador", "2"),
    ("SP", "Deputado Estadual", "70"),
]
RECEITAS_COLUNAS = "DT_GERACAO HH_GERACAO AA_ELEICAO ST_TURNO TP_PRESTACAO_CONTAS DT_PRESTACAO_CONTAS SQ_PRESTADOR_CONTAS SG_UF SG_UE DS_CARGO SQ_CANDIDATO NR_CPF_CANDIDATO NR_CPF_CNPJ_DOADOR NM_DOADOR SQ_RECEITA DT_RECEITA VR_RECEITA".split()  # noqa: E501
DESPESAS_COLUNAS = "DT_GERACAO HH_GERACAO AA_ELEICAO ST_TURNO TP_PRESTACAO_CONTAS DT_PRESTACAO_CONTAS SQ_PRESTADOR_CONTAS SG_UF SG_UE DS_CARGO SQ_CANDIDATO NR_CPF_CANDIDATO NR_CPF_CNPJ_FORNECEDOR NM_FORNECEDOR SQ_DESPESA DT_DESPESA VR_DESPESA_CONTRATADA".split()  # noqa: E501
#         sq, valor da receita
RECEITAS = [("1001", "1000,00"), ("1001", "250,50"), ("1002", "300,00")]
#         sq, valor da despesa contratada
DESPESAS = [("1001", "400,00")]


def _pacote(destino: Path, membros: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(destino, "w") as pacote:
        for nome, conteudo in membros.items():
            pacote.writestr(nome, conteudo)
    return destino


CODIGO_DO_CARGO = {"Deputado Federal": "6", "Senador": "5", "Deputado Estadual": "7", "Governador": "3"}


def _vagas() -> bytes:
    gerais = [
        {
            "SG_UF": uf,
            "SG_UE": uf,
            "DS_CARGO": cargo,
            "QT_VAGA": vagas,
            "CD_CARGO": CODIGO_DO_CARGO[cargo],
            "CD_ELEICAO": "544",
            "DS_ELEICAO": "Eleição Geral Federal 2022",
            "DT_POSSE": "01/02/2023",
        }
        for uf, cargo, vagas in VAGAS
    ]
    # o arquivo real de 2022 traz também a eleição suplementar de governador de Roraima: não é eleição geral
    suplementar = {
        "SG_UF": "RR",
        "SG_UE": "RR",
        "DS_CARGO": "Governador",
        "QT_VAGA": "1",
        "CD_CARGO": "3",
        "CD_ELEICAO": "6278",
        "DS_ELEICAO": "Eleição Suplementar Governador 2026",
        "DT_POSSE": "01/01/2027",
    }
    municipais = [
        {"SG_UF": "RJ", "SG_UE": ue, "DS_CARGO": cargo, "QT_VAGA": vagas, "CD_CARGO": codigo, "CD_ELEICAO": "700",
         "DS_ELEICAO": "Eleições Ordinárias 2022", "DT_POSSE": "01/01/2023", "NM_UE": f"MUNICIPIO {ue}"}
        for ue, cargo, vagas, codigo in (("60011", "Prefeito", "1", "11"), ("60011", "Vereador", "3", "13"),
                                         ("60012", "Vereador", "3", "13"))
    ]  # fmt: skip
    return _tabela(VAGAS_COLUNAS, [*gerais, suplementar, *municipais])


def _contas(
    colunas: Sequence[str], linhas: Sequence[tuple[str, str]], chave: str, valor: str, sufixo: str
) -> bytes:
    return _tabela(
        colunas,
        [
            {"AA_ELEICAO": "2022", "ST_TURNO": "1", "TP_PRESTACAO_CONTAS": "FINAL", "DT_PRESTACAO_CONTAS": "12/12/2022",
             "SQ_PRESTADOR_CONTAS": f"90{sq}", "SG_UF": UF_DE[sq], "SG_UE": UF_DE[sq], "DS_CARGO": "Deputado Federal",
             "SQ_CANDIDATO": sq, "NR_CPF_CANDIDATO": "12345678900", "NR_CPF_CNPJ_DOADOR": "11122233344",
             "NM_DOADOR": "DOADOR SIGILOSO", "NR_CPF_CNPJ_FORNECEDOR": "55566677788", "NM_FORNECEDOR": "FORNECEDOR SIGILOSO",
             chave: f"{i}{sq}", sufixo: "10/09/2022", valor: v}
            for i, (sq, v) in enumerate(linhas, start=1)
        ],
    )  # fmt: skip


def _receitas() -> bytes:
    return _contas(RECEITAS_COLUNAS, RECEITAS, "SQ_RECEITA", "VR_RECEITA", "DT_RECEITA")


def _despesas() -> bytes:
    return _contas(DESPESAS_COLUNAS, DESPESAS, "SQ_DESPESA", "VR_DESPESA_CONTRATADA", "DT_DESPESA")
