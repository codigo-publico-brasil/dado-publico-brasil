"""Dados sintéticos das emendas parlamentares (pacote .zip com três CSVs em latin-1, como o real); sem rede.

Emendas: uma individual com autor, uma antiga sem código nem autor ("Sem informação") e uma de relator-geral.
Favorecidos: pessoa jurídica, unidade gestora, pessoa física (CPF mascarado) e inscrição genérica: só os dois
primeiros podem chegar ao raw.
"""

import csv
import io
import zipfile
from pathlib import Path

from dado_publico_brasil.ingestion import contract as contracts

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

MES = 202401  # nome dos CSVs; o mesmo pacote responde por todos os meses de 2024 (linhas iguais se fundem)
DESPESAS = [
    ";".join(
        [
            "Ano e mês do lançamento",
            "Código Órgão Superior",
            "Nome Órgão Superior",
            "Código Órgão Subordinado",
            "Nome Órgão Subordinado",
            "Código Unidade Gestora",
            "Nome Unidade Gestora",
            "Código Gestão",
            "Nome Gestão",
            "Código Unidade Orçamentária",
            "Nome Unidade Orçamentária",
            "Código Função",
            "Nome Função",
            "Código Subfução",
            "Nome Subfunção",
            "Código Programa Orçamentário",
            "Nome Programa Orçamentário",
            "Código Ação",
            "Nome Ação",
            "Código Plano Orçamentário",
            "Plano Orçamentário",
            "Código Programa Governo",
            "Nome Programa Governo",
            "UF",
            "Município",
            "Código Subtítulo",
            "Nome Subtítulo",
            "Código Localizador",
            "Nome Localizador",
            "Sigla Localizador",
            "Descrição Complementar Localizador",
            "Código Autor Emenda",
            "Nome Autor Emenda",
            "Código Categoria Econômica",
            "Nome Categoria Econômica",
            "Código Grupo de Despesa",
            "Nome Grupo de Despesa",
            "Código Elemento de Despesa",
            "Nome Elemento de Despesa",
            "Código Modalidade da Despesa",
            "Modalidade da Despesa",
            "Valor Empenhado (R$)",
            "Valor Liquidado (R$)",
            "Valor Pago (R$)",
            "Valor Restos a Pagar Inscritos (R$)",
            "Valor Restos a Pagar Cancelado (R$)",
            "Valor Restos a Pagar Pagos (R$)",
        ]
    ),
    "2024/01;52000;Ministério A;52904;Órgão B;167399;UNIDADE GESTORA C;00001;TESOURO NACIONAL;52921;UNIDADE D;05;"
    "Defesa nacional;331;Proteção;0032;PROGRAMA;2004;ACAO;0007;PLANO;00;Sem informação;;;20040001;SUBTITULO;0001;"
    "LOCALIZADOR;-1;Sem informação;;SEM EMENDA;3;DESPESAS CORRENTES;3;Outras Despesas Correntes;30;Material;90;"
    "Aplicações Diretas;805942,86;698956,52;743598,53;0,00;0,00;27426,73",
]
COMPRAS = [
    "Número do Contrato;Objeto;Fundamento Legal;Modalidade Compra;Situação Contrato;Código Órgão Superior;"
    "Nome Órgão Superior;Código Órgão;Nome Órgão;Código UG;Nome UG;Data Assinatura Contrato;Data Publicação DOU;"
    "Data Início Vigência;Data Fim Vigência;Código Contratado;Nome Contratado;Valor Inicial Compra;"
    "Valor Final Compra;Número Licitação;Código UG Licitação;Nome UG Licitação;Código Modalidade Compra Licitação;"
    "Modalidade Compra Licitação",
    "000012024;Serviço de limpeza. CPF 123.456.789-09;;Pregão;Ativo;30000;Ministério A;30108;Órgão B;200384;UG C;"
    "24/01/2024;29/01/2024;24/01/2024;24/01/2025;12345678000199;EMPRESA EXEMPLO LTDA;205690,0000;205690,0000;"
    "000012024;200384;UG C;5;Pregão",
    "000022024;Serviço pessoal;;Dispensa;Ativo;30000;Ministério A;30108;Órgão B;200384;UG C;25/01/2024;;25/01/2024;"
    "25/01/2025;12345678909;PESSOA EXEMPLO;1000,0000;1000,0000;;;;;",
    "000032024;Informação protegida por sigilo nos termos da legislação vigente;;Sem Informação;Não se aplica;30000;"
    "Ministério A;30108;Órgão B;200384;UG C;26/01/2024;;26/01/2024;26/01/2025;-11;Sigiloso;500,0000;500,0000;;;;;",
]
ITENS_COMPRA = [
    "Código Órgão;Nome Órgão;Código UG;Nome UG;Número Contrato;Código Item Compra;Descrição Item Compra;"
    "Descrição Complementar Item Compra;Quantidade Item;Valor Item",
    "30108;Órgão B;200384;UG C;000012024;200384059006220240001;LIMPEZA;LIMPEZA DE PREDIO;1,5;205690,00",
    "30108;Órgão B;200384;UG C;000022024;200384059006220240002;SERVICO;CONTRATADO CPF 987.654.321-00;1;1000,00",
]
TERMOS_ADITIVOS = [
    "Número Contrato;Código Órgão Superior;Nome Órgão Superior;Código Órgão;Nome Órgão;Código UG;Nome UG;"
    "Número Termo Aditivo;Data Publicação;Objeto",
    "000012024;30000;Ministério A;30108;Órgão B;200384;UG C;000012024;16/12/2024;PRORROGACAO DE VIGENCIA",
    "000022024;30000;Ministério A;30108;Órgão B;200384;UG C;000012024;17/12/2024;ADITIVO DE PESSOA CPF 987.654.321-00",
]


LICITACOES = [
    "Número Licitação;Código UG;Nome UG;Código Modalidade Compra;Modalidade Compra;Número Processo;Objeto;"
    "Situação Licitação;Código Órgão Superior;Nome Órgão Superior;Código Órgão;Nome Órgão;UF;Município;"
    "Data Resultado Compra;Data Abertura;Valor Licitação",
    "000012024;200384;UG C;5;Pregão;23000.000001/2024-01;Serviço de limpeza. CPF 123.456.789-09;Publicado;30000;"
    "Ministério A;30108;Órgão B;DF;BRASÍLIA;24/01/2024;10/01/2024;205690,5000",
    "000022024;200384;UG C;6;Dispensa;23000.000002/2024-02;Material de consumo;Encerrado;30000;Ministério A;30108;"
    "Órgão B;DF;BRASÍLIA;25/01/2024;;1000,0000",
]
ITENS_LICITACAO = [
    "Número Licitação;Código UG;Nome UG;Código Modalidade Compra;Modalidade Compra;Número Processo;Código Órgão;"
    "Nome Órgão;Código Item Compra;Descrição;Quantidade Item;Valor Item;Código Vencedor;Nome Vencedor",
    "000012024;200384;UG C;5;Pregão;23000.000001/2024-01;30108;Órgão B;200384050000120240001;LIMPEZA;1,5000;"
    "205690,5000;12345678000199;EMPRESA EXEMPLO LTDA",
    "000022024;200384;UG C;6;Dispensa;23000.000002/2024-02;30108;Órgão B;200384060000220240001;"
    "SERVICO DE CPF 987.654.321-00;2,0000;1000,0000;12345678909;PESSOA EXEMPLO",
]
PARTICIPANTES_LICITACAO = [
    "Número Licitação;Código UG;Nome UG;Código Modalidade Compra;Modalidade Compra;Número Processo;Código Órgão;"
    "Nome Órgão;Código Item Compra;Descrição Item Compra;Código Participante;Nome Participante;Flag Vencedor",
    "000012024;200384;UG C;5;Pregão;23000.000001/2024-01;30108;Órgão B;200384050000120240001;LIMPEZA;"
    "12345678000199;EMPRESA EXEMPLO LTDA;SIM",
    "000012024;200384;UG C;5;Pregão;23000.000001/2024-01;30108;Órgão B;200384050000120240001;LIMPEZA;"
    "12345678909;PESSOA EXEMPLO;NÃO",
]
EMPENHOS_LICITACAO = [
    "Número Licitação;Código UG;Nome UG;Código Modalidade Compra;Modalidade Compra;Número Processo;Código Empenho;"
    "Data Emissão Empenho;Observação Empenho;Valor Empenho (R$)",
    "000012024;200384;UG C;5;Pregão;23000.000001/2024-01;200384000012024NE000001;30/01/2024;PAGAMENTO;205690,5000",
]


def _csv(linhas: list[str]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", quoting=csv.QUOTE_ALL)
    for linha in linhas:
        escritor.writerow(next(csv.reader([linha], delimiter=";")))
    return saida.getvalue().encode("latin-1")


def transparencia_files(pasta: Path) -> dict[str, Path]:
    """Os pacotes sintéticos, pela URL oficial de cada dataset (as emendas usam o mesmo arquivo; os mensais, um por mês)."""
    pasta.mkdir(parents=True, exist_ok=True)
    contrato = contracts.find("transparencia")
    destino = pasta / "UNICO.zip"
    with zipfile.ZipFile(destino, "w") as pacote:
        pacote.writestr("EmendasParlamentares.csv", _csv(EMENDAS))
        pacote.writestr("EmendasParlamentares_Convenios.csv", _csv(CONVENIOS))
        pacote.writestr("EmendasParlamentares_PorFavorecido.csv", _csv(FAVORECIDOS))
    despesas = pasta / "despesas.zip"
    with zipfile.ZipFile(despesas, "w") as pacote:
        pacote.writestr(f"{MES}_Despesas.csv", _csv(DESPESAS))
    compras = pasta / "compras.zip"
    with zipfile.ZipFile(compras, "w") as pacote:
        pacote.writestr(f"{MES}_Compras.csv", _csv(COMPRAS))
        pacote.writestr(f"{MES}_ItemCompra.csv", _csv(ITENS_COMPRA))
        pacote.writestr(f"{MES}_TermoAditivo.csv", _csv(TERMOS_ADITIVOS))
    licitacoes = pasta / "licitacoes.zip"
    with zipfile.ZipFile(licitacoes, "w") as pacote:  # nomes com acento, como no pacote oficial
        pacote.writestr(f"{MES}_Licitação.csv", _csv(LICITACOES))
        pacote.writestr(f"{MES}_ItemLicitação.csv", _csv(ITENS_LICITACAO))
        pacote.writestr(f"{MES}_ParticipantesLicitação.csv", _csv(PARTICIPANTES_LICITACAO))
        pacote.writestr(f"{MES}_EmpenhosRelacionados.csv", _csv(EMPENHOS_LICITACAO))
    mensais = {
        "despesas": despesas,
        "compras": compras,
        "compras_itens": compras,
        "compras_termos_aditivos": compras,
        "licitacoes": licitacoes,
        "licitacoes_itens": licitacoes,
        "licitacoes_participantes": licitacoes,
        "licitacoes_empenhos": licitacoes,
    }
    return {
        **{contrato.url(nome, 202400 + mes): mensais[nome] for nome in mensais for mes in range(1, 13)},
        **{contrato.url(nome): destino for nome in contrato.datasets if nome not in mensais},
    }
