"""Arquivo mensal sintético das Pessoas Expostas Politicamente (formato real: CSV latin-1 dentro de um .zip)."""

import zipfile
from pathlib import Path

from dado_publico_brasil.ingestion import contract as contracts

CABECALHO = (
    "CPF;Nome_PEP;Sigla_Função;Descrição_Função;Nível_Função;Nome_Órgão;Data_Início_Exercício;"
    "Data_Fim_Exercício;Data_Fim_Carência"
)
LINHAS = [
    "***.111.222-**;PESSOA EXEMPLO A;001;PRESIDENTE DA REPUBLICA;001;PRESIDENCIA DA REPUBLICA;01/01/2019;01/01/2023;01/01/2028",
    "***.111.222-**;PESSOA EXEMPLO B;001;PRESIDENTE DA REPUBLICA;001;PRESIDENCIA DA REPUBLICA;01/01/2023;Não informada;Não informada",
    "***.333.444-**;PESSOA EXEMPLO C;001;VICE-PRESIDENTE DA REPUBLICA;021;VICE-PRESIDENCIA DA REPUBLICA;01/01/2023;Não informada;Não informada",
    "***.555.666-**;PESSOA EXEMPLO D;001;MINISTRO DE ESTADO;005;MINISTERIO DA SAUDE;01/01/2023;10/03/2025;10/03/2030",
    "***.777.888-**;PESSOA EXEMPLO E;001;MINISTRO DE ESTADO;005;MINISTERIO DA SAUDE;10/03/2025;Não informada;Não informada",
    "***.999.000-**;PESSOA EXEMPLO F;001;MINISTRO DE ESTADO;005;MINISTERIO DA FAZENDA;Não informada;Não informada;Não informada",
    # fora do topo do Executivo: a carga descarta
    "***.123.123-**;PESSOA EXEMPLO G;DIRE01;VICE-PRESIDENTE;;CAIXA;09/12/2020;19/01/2023;19/01/2028",
    "***.321.321-**;PESSOA EXEMPLO H;CAS-1;DIR. SUPERINTENDENTE;;SUDEMA;21/12/2019;Não informada;Não informada",
]


def pep_files(pasta: Path) -> dict[str, Path]:
    """O pacote sintético em cada mês que o plano pode pedir (da primeira partição ao fim de 2026), pela URL oficial."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "pep.zip"
    with zipfile.ZipFile(destino, "w") as pacote:
        pacote.writestr("202609_PEP.csv", "\n".join([CABECALHO, *LINHAS]).encode("latin-1"))
    contrato = contracts.find("pep")
    return {contrato.url("dirigentes", mes): destino for mes in range(202609, 202613)}
