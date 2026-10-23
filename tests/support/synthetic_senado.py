"""Dados sintéticos no formato real do Senado (JSON aninhado); sem rede.

Três senadores (dois no cadastro, um só nos votos) e duas votações de 2024: uma nominal e uma secreta.
A matéria 700 (PLP) é votada nas duas. O nome de um senador repete o de uma pessoa da Câmara de propósito:
pessoas de fontes diferentes nunca são ligadas por nome.
"""

import json
from pathlib import Path

from plataforma_dados.ingestion import contract as contracts


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
        "descricaoVotoParlamentar": None,
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
    saida: dict[str, Path] = {}
    for dataset, partition, payload in (("senadores", 57, senadores), ("votacoes", 2024, votacoes)):
        file = pasta / f"senado-{dataset}-{partition}.json"
        file.write_text(json.dumps(payload), encoding="utf-8")
        saida[contract.url(dataset, partition)] = file
    return saida
