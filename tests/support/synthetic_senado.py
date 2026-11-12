"""Dados sintéticos no formato real do Senado (JSON aninhado); sem rede.

Três senadores (dois no cadastro, um só nos votos) e duas votações de 2024: uma nominal e uma secreta.
A matéria 700 (PLP) é votada nas duas. O nome de um senador repete o de uma pessoa da Câmara de propósito:
pessoas de fontes diferentes nunca são ligadas por nome.
"""

import json
from pathlib import Path

from dado_publico_brasil.ingestion import contract as contracts

CRLF = chr(13) + chr(10)  # o CSV do Senado termina as linhas assim


def _parlamentar(codigo: str, nome: str, civil: str, sexo: str) -> dict[str, object]:
    return {
        "IdentificacaoParlamentar": {
            "CodigoParlamentar": codigo,
            "NomeParlamentar": nome,
            "NomeCompletoParlamentar": civil,
            "SexoParlamentar": sexo,
        },
        "Mandatos": {
            "Mandato": [
                {
                    "CodigoMandato": f"m{codigo}",
                    "UfParlamentar": "SP",
                    "DescricaoParticipacao": "Titular",
                    "Titular": {
                        "DescricaoParticipacao": "Titular",
                        "CodigoParlamentar": codigo,
                        "NomeParlamentar": nome,
                    },
                    "PrimeiraLegislaturaDoMandato": {
                        "NumeroLegislatura": "56",
                        "DataInicio": "2019-02-01",
                        "DataFim": "2023-01-31",
                    },
                    "SegundaLegislaturaDoMandato": {
                        "NumeroLegislatura": "57",
                        "DataInicio": "2023-02-01",
                        "DataFim": "2027-01-31",
                    },
                    "Exercicios": {
                        "Exercicio": [
                            {
                                "CodigoExercicio": f"e{codigo}",
                                "DataInicio": "2019-02-01",
                                "DataFim": "2020-05-01",
                                "DataLeitura": "2019-02-04",
                                "SiglaCausaAfastamento": "LIC",
                                "DescricaoCausaAfastamento": "Licença",
                            }
                        ]
                    },
                }
            ]
        },
    }


def _voto(codigo: int, nome: str, partido: str, uf: str, sigla: str) -> dict[str, object]:
    return {
        "codigoParlamentar": codigo,
        "nomeParlamentar": nome,
        "sexoParlamentar": "M",
        "siglaPartidoParlamentar": partido,
        "siglaUFParlamentar": uf,
        "siglaVotoParlamentar": sigla,
        "descricaoVotoParlamentar": "Voto registrado",
    }


def _votacao(
    codigo: int, data: str, secreta: str, resultado: str, votos: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "codigoSessaoVotacao": codigo,
        "codigoSessao": 1,
        "dataSessao": data,
        "siglaTipoSessao": "DOR",
        "votacaoSecreta": secreta,
        "resultadoVotacao": resultado,
        "totalVotosSim": 1 if secreta == "N" else None,
        "totalVotosNao": 1 if secreta == "N" else None,
        "totalVotosAbstencao": None,
        "descricaoVotacao": "Votação nominal do PLP 700.",
        "codigoMateria": 700,
        "idProcesso": 1,
        "identificacao": "PLP 700/2023",
        "sigla": "PLP",
        "numero": "700",
        "ano": 2023,
        "dataApresentacao": "2023-05-02",
        "ementa": "ALTERA A LEI COMPLEMENTAR X.\n",
        "informeLegislativo": {"siglaColegiado": "PLEN", "nomeColegiado": "Plenário do Senado Federal"},
        "votos": votos,
    }


def _colegiado(codigo: str, sigla: str, nome: str, casa: str) -> dict[str, str]:
    return {
        "Codigo": codigo,
        "Sigla": sigla,
        "Nome": nome,
        "DataInicio": "1900-01-01",
        "Publica": "S",
        "SiglaTipoColegiado": "PERMANENTE",
        "DescricaoTipoColegiado": "Comissão Permanente",
        "SiglaCasa": casa,
    }


def senado_files(pasta: Path) -> dict[str, Path]:
    """Os arquivos sintéticos do Senado, por URL oficial (como o extrator os pede)."""
    pasta.mkdir(parents=True, exist_ok=True)
    contract = contracts.find("senado")
    senadores = {
        "ListaParlamentarLegislatura": {
            "Parlamentares": {
                "Parlamentar": [
                    _parlamentar("5000", "BETO BARREIRAS", "Roberto Barreiras", "Masculino"),
                    _parlamentar("5001", "Ana Árvore", "Ana Aparecida da Silva", "Feminino"),
                    _parlamentar("5003", "BIA SOUZA", "Bia Souza", "Feminino"),
                ]
            }
        }
    }
    votacoes = [
        _votacao(
            9001,
            "2024-05-10",
            "N",
            "A",
            [
                _voto(5000, "Beto Barreiras", "AAA", "SP", "Sim"),
                _voto(5001, "Ana Árvore", "BBB", "RJ", "Não"),
            ],
        ),
        _votacao(
            9002,
            "2024-06-11",
            "S",
            "R",
            [_voto(5000, "Beto Barreiras", "AAA", "SP", "Votou"), _voto(5002, "DIOGO", "CCC", "MG", "Votou")],
        ),
    ]
    colegiados = {
        "ListaColegiados": {
            "Colegiados": {
                "Colegiado": [
                    _colegiado("1", "PLEN", "Plenário do Senado Federal", "SF"),
                    _colegiado("2", "CMO", "Comissão Mista de Orçamento", "CN"),
                ]
            }
        }
    }
    saida: dict[str, Path] = {}
    arquivo = pasta / "senado-colegiados.json"
    arquivo.write_text(json.dumps(colegiados), encoding="utf-8")
    saida[contract.url("colegiados")] = arquivo
    for dataset, partition, payload in (("senadores", 57, senadores), ("votacoes", 2024, votacoes)):
        file = pasta / f"senado-{dataset}-{partition}.json"
        file.write_text(json.dumps(payload), encoding="utf-8")
        saida[contract.url(dataset, partition)] = file
    # CEAPS: ISO-8859-1, aviso antes do cabeçalho, vírgula decimal. As competências são de 2020 (dentro do exercício
    # sintético dos senadores) para a regra de ligação ter o que casar; o arquivo é o de 2024 do plano de teste.
    linhas = [
        '"ULTIMA ATUALIZACAO";"12/11/2026 02:01"',
        '"ANO";"MES";"SENADOR";"TIPO_DESPESA";"CNPJ_CPF";"FORNECEDOR";"DOCUMENTO";"DATA";"DETALHAMENTO";'
        '"VALOR_REEMBOLSADO";"COD_DOCUMENTO"',
        '"2020";"3";"BETO BARREIRAS";"Divulgação da atividade parlamentar";"11.222.333/0001-81";"GRÁFICA X LTDA";'
        '"77";"05/03/2020";"";"1500,75";"9001"',
        '"2020";"3";"BETO BARREIRAS";"Divulgação da atividade parlamentar";"123.456.789-09";"FULANO DE TAL";'
        '"78";"06/03/2020";"Serviço do CPF 123.456.789-09";"300";"9002"',
        '"2020";"3";"SENADOR SEM CADASTRO";"Divulgação da atividade parlamentar";"";"";"";"";"";"10";"9003"',
    ]
    ceaps = pasta / "senado-ceaps-2024.csv"
    ceaps.write_bytes(CRLF.join(linhas).encode("cp1252") + CRLF.encode())
    saida[contract.url("ceaps", 2024)] = ceaps
    return saida
