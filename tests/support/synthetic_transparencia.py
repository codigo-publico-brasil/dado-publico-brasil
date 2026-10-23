"""Dados sintéticos das emendas parlamentares (pacote .zip com três CSVs em latin-1, como o real); sem rede.

Emendas: uma individual com autor, uma antiga sem código nem autor ("Sem informação") e uma de relator-geral.
Favorecidos: pessoa jurídica, unidade gestora, pessoa física (CPF mascarado) e inscrição genérica: só os dois
primeiros podem chegar ao raw.
"""

import csv
import io
import zipfile
from pathlib import Path

from plataforma_dados.ingestion import contract as contracts

EMENDAS = [
    "Código da Emenda;Ano da Emenda;Tipo de Emenda;Código do Autor da Emenda;Nome do Autor da Emenda;Número da emenda;"
    "Localidade de aplicação do recurso;Código Município IBGE;Município;Código UF IBGE;UF;Região;Código Função;"
    "Nome Função;Código Subfunção;Nome Subfunção;Código Programa;Nome Programa;Código Ação;Nome Ação;"
    "Código Plano Orçamentário;Nome Plano Orçamentário;Valor Empenhado;Valor Liquidado;Valor Pago;"
    "Valor Restos A Pagar Inscritos;Valor Restos A Pagar Cancelados;Valor Restos A Pagar Pagos",
    "202471280001;2024;Emenda Individual - Transferências com Finalidade Definida;7128;FULANO DE TAL;0001;"
    "ALVORADA DO SUL - PR;4100806;ALVORADA DO SUL;4100000;PARANÁ;Sul;10;Saúde;301;Atenção básica;2015;"
    "SUS;8581;ESTRUTURACAO DA REDE;0000;DESPESAS DIVERSAS;499995,00;250000,50;100000,00;0,00;0,00;0,00",
    "Sem informação;2014;Emenda Individual - Transferências com Finalidade Definida;S/I;Sem informação;S/I;"
    "MULTIPLO;9999999;MULTIPLO;9999999;MULTIPLO;Sem informação;12;Educação;361;Ensino;2030;EDUCACAO;20RP;"
    "APOIO;0000;DIVERSAS;1000,00;0,00;0,00;0,00;0,00;1000,00",
    "202490020001;2024;Emenda de Relator;9002;RELATOR GERAL;0001;NACIONAL;0;NACIONAL;0;NACIONAL;Nacional;4;"
    "Administração;122;Administração geral;0032;PROGRAMA;0Z00;ACAO;0000;PLANO;75000,00;0,00;0,00;0,00;0,00;0,00",
]
CONVENIOS = [
    "Código da Emenda;Código Função;Nome Função;Código Subfunção;Nome Subfunção;Localidade do gasto;Tipo de Emenda;"
    "Data Publicação Convênio;Convenente;Objeto Convênio;Número Convênio;Valor Convênio",
    "202471280001;10;Saúde;302;Assistência hospitalar;ALVORADA DO SUL (PR);Emenda Individual;06/01/2025;"
    "PREFEITURA MUNICIPAL;AQUISICAO DE EQUIPAMENTO;825378;1450000,00",
]
FAVORECIDOS = [
    "Código da Emenda;Código do Autor da Emenda;Nome do Autor da Emenda;Número da emenda;Tipo de Emenda;Ano/Mês;"
    "Código do Favorecido;Favorecido;Natureza Jurídica;Tipo Favorecido;UF Favorecido;Município Favorecido;Valor Recebido",
    "202471280001;7128;FULANO DE TAL;0001;Emenda Individual;202410;07121982000119;2M CONSTRUTORA LTDA;"
    "Sociedade Empresária Limitada;Pessoa Jurídica;PR;ALVORADA DO SUL;83346,73",
    "202471280001;7128;FULANO DE TAL;0001;Emenda Individual;202411;195017;CIA DE DESENVOLVIMENTO;"
    "Administração Pública;Unidade Gestora;DF;BRASILIA;1000,00",
    "202471280001;7128;FULANO DE TAL;0001;Emenda Individual;202411;***.638.223-**;CIDADAO COMUM DA SILVA;"
    "Pessoa Física;Pessoa Fisica;PR;ALVORADA DO SUL;1500,00",
    "202471280001;7128;FULANO DE TAL;0001;Emenda Individual;202411;EXPF00001;OUTRO CIDADAO;"
    "Pessoa Física;Inscrição Genérica;PR;ALVORADA DO SUL;800,00",
]


def _csv(linhas: list[str]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL)
    for linha in linhas:
        escritor.writerow(next(csv.reader([linha], delimiter=";")))
    return saida.getvalue().encode("latin-1")


def transparencia_files(pasta: Path) -> dict[str, Path]:
    """O pacote sintético, pela URL oficial de cada dataset (os três usam o mesmo arquivo)."""
    pasta.mkdir(parents=True, exist_ok=True)
    contrato = contracts.find("transparencia")
    destino = pasta / "UNICO.zip"
    with zipfile.ZipFile(destino, "w") as pacote:
        pacote.writestr("EmendasParlamentares.csv", _csv(EMENDAS))
        pacote.writestr("EmendasParlamentares_Convenios.csv", _csv(CONVENIOS))
        pacote.writestr("EmendasParlamentares_PorFavorecido.csv", _csv(FAVORECIDOS))
    return {contrato.url(nome): destino for nome in contrato.datasets}
