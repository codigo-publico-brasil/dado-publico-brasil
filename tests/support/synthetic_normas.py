"""Dados sintéticos no formato real das normas, vetos e da Constituição; sem rede.

Três normas de 2024 (uma lei, uma emenda e um decreto), um veto da matéria 700 com dois dispositivos (um votado em
painel) e a Constituição com a Emenda 99 (e a 98, só no Senado). O texto da Constituição é um HTML mínimo no jeito
do arquivo da Câmara: um parágrafo por dispositivo.
"""

import json
from pathlib import Path

from dado_publico_brasil.ingestion import contract as contracts

BASE = "https://legis.senado.leg.br/dadosabertos"
CONSTITUICAO_ID = "579494"


def _norma(
    id_: str, tipo: str, descricao: str, numero: str, nome: str, ementa: str, data: str, apelido: str
) -> dict[str, str]:
    return {
        "id": id_,
        "tipo": tipo,
        "descricao": descricao,
        "numero": numero,
        "norma": nome.upper().replace(" ", "-"),
        "normaNome": nome,
        "ementa": ementa,
        "dataassinatura": data,
        "anoassinatura": data[-4:],
        "apelido": apelido,
    }


def _publicacao(id_: str, tipo: str, data: str) -> dict[str, str]:
    return {
        "id": id_,
        "tipo": tipo,
        "fonte": f"Diário Oficial da União de {data}",
        "siglaFonte": f"DOU-{data}",
        "data": data,
        "pagina": "1",
        "coluna": "2",
        "dispositivo": f"Publicação [DOU de {data}] (p. 1, col. 2)",
        "temTexto": "S",
    }


def _vide(posterior: str, nome: str, comentario: str) -> dict[str, str]:
    return {
        "codnormaposterior": posterior,
        "datAssinatura": "15/02/2024",
        "nomeNormaPosterior": nome,
        "datapub": "16/02/2024",
        "nomePub": f"Publicação de {nome}",
        "comentario": comentario,
    }


def _detalhe(item: str, tipo: str, numero: str, nome: str, ementa: str, vides: object) -> dict[str, object]:
    return {
        "DetalheDocumento": {
            "documentos": {
                "documento": [
                    {
                        "id": item,
                        "identificacao": {
                            "tipo": tipo,
                            "descricao": nome.split(" nº")[0],
                            "numero": numero,
                            "norma": nome.upper().replace(" ", "-"),
                            "normaNome": nome,
                            "dataassinatura": "28/06/2024",
                            "apelido": "",
                            "urlDocumento": f"https://normas.leg.br/?urn=teste:{item}",
                        },
                        "publicacoes": {"publicacao": [_publicacao(f"5{item}", "PUB", "01/07/2024")]},
                        "vides": vides,  # lista de relações ou "" quando não há, como a API devolve
                        "ementa": ementa,
                    }
                ]
            }
        }
    }


DETALHES = {
    "1001": _detalhe(
        "1001",
        "LEI-n",
        "14999",
        "Lei nº 14.999 de 28/06/2024",
        "Altera a Lei Complementar X.",
        {
            "vide": [
                _vide(
                    "1002", "Emenda Constitucional nº 99 de 15/02/2024", "Declaração de Alteração Permanente"
                )
            ]
        },
    ),
    "1002": _detalhe(
        "1002", "EMC-n", "99", "Emenda Constitucional nº 99 de 15/02/2024", "Altera a Constituição.", ""
    ),
    CONSTITUICAO_ID: _detalhe(
        CONSTITUICAO_ID,
        "CON-v",
        "",
        "Constituição da República Federativa do Brasil de 05/10/1988",
        "Constituição.",
        {
            "vide": [
                _vide(
                    "1002", "Emenda Constitucional nº 99 de 15/02/2024", "Declaração de Alteração Permanente"
                ),
                _vide(
                    "1003", "Emenda Constitucional nº 98 de 10/01/2023", "Declaração de Alteração Permanente"
                ),
                _vide(
                    "1004", "Emenda Constitucional nº 97 de 10/01/2022", "Declaração de Alteração Permanente"
                ),
            ]
        },
    ),
}

DISPOSITIVOS = {
    "8001": {
        "ResultadoVetoMateriaCN": {
            "Veto": {
                "Codigo": "7001",
                "Dispositivos": {
                    "Dispositivo": [
                        {
                            "Codigo": "9001",
                            "Identificador": "5.24.001",
                            "Descricao": "art. 2º",
                            "Conteudo": "Texto que foi vetado.",
                            "RazaoVeto": "A proposição contraria o interesse público.",
                            "Situacao": "Rejeitado",
                            "PossuiVotos": "Sim",
                            "TipoVotacao": "Painel",
                            "DataSessao": "2024-09-10",
                        },
                        {
                            "Codigo": "9002",
                            "Identificador": "5.24.002",
                            "Descricao": "art. 3º",
                            "Conteudo": "Outro texto vetado.",
                            "RazaoVeto": "Há vício de iniciativa.",
                            "Situacao": "Não Apreciado",
                            "PossuiVotos": "Não",
                        },
                        {  # veto total: a fonte não traz `Codigo`, só o identificador
                            "Identificador": "5.24.000",
                            "Descricao": "Veto total",
                            "Conteudo": "Veto total aposto ao projeto.",
                            "RazaoVeto": "A proposição é inconstitucional.",
                            "Situacao": "Mantido",
                            "PossuiVotos": "Não",
                        },
                    ]
                },
            }
        }
    }
}

VOTOS = {
    "9001": {
        "ResultadoVetoDispositivoCN": {
            "Votacao": {
                "ParteVetada": "art. 2º",
                "TipoVotacao": "Painel",
                "Sessao": "SESSÃO CONJUNTA Nº 003",
                "Camara": {
                    "Voto": [
                        {
                            "NomeParlamentar": "BIA",
                            "PartidoParlamentar": "BBB",
                            "UfParlamentar": "RJ",
                            "TipoVoto": "Sim",
                        },
                        {
                            "NomeParlamentar": "Carlos",
                            "PartidoParlamentar": "CCC",
                            "UfParlamentar": "MG",
                            "TipoVoto": "Não",
                        },
                    ]
                },
                "Senado": {
                    "Voto": [
                        {
                            "NomeParlamentar": "BETO BARREIRAS",
                            "PartidoParlamentar": "AAA",
                            "UfParlamentar": "SP",
                            "TipoVoto": "Sim",
                        }
                    ]
                },
            }
        }
    }
}

HTML = """<html><body>
<p>CÂMARA DOS DEPUTADOS Centro de Documentação e Informação</p>
<p>PREÂMBULO</p>
<p>Nós, representantes do povo brasileiro.</p>
<p>TÍTULO I DOS PRINCÍPIOS FUNDAMENTAIS</p>
<p>Art. 1º A República Federativa do Brasil constitui-se em Estado democrático de direito e tem como fundamentos:</p>
<p>I - a soberania;</p>
<p>II - a cidadania.</p>
<p>Parágrafo único . Todo o poder emana do povo.</p>
<p>CAPÍTULO II DOS DIREITOS SOCIAIS</p>
<p>Art. 6º São direitos sociais a educação e a saúde. (Redação dada pela Emenda Constitucional nº 99, de 2024)</p>
<p>Art. 7º São direitos dos trabalhadores:</p>
<p>I - relação de emprego protegida;</p>
<p>a) uma alínea de teste;</p>
<p>§ 1º Um parágrafo (Incluído pelas Emendas Constitucionais nºs 20 e 41, de 1998 e 2003)</p>
<p>Art. 8º Dispositivo antigo. (Revogado pela Emenda Constitucional nº 98, de 2023)</p>
<p>Brasília, 5 de outubro de 1988</p>
<p>Nome Exemplo</p>
</body></html>"""

HTML_ADCT = """<html><body>
<p>CÂMARA DOS DEPUTADOS Centro de Documentação e Informação</p>
<p>Art. 1º O Presidente da República prestará o compromisso.</p>
<p>§ 1º Disposição transitória. (Incluído pela Emenda Constitucional nº 99, de 2024)</p>
</body></html>"""


def normas_files(pasta: Path) -> dict[str, Path]:
    """Os arquivos sintéticos por URL oficial: catálogo e vetos de 2024, a Constituição no Senado e o HTML da Câmara."""
    pasta.mkdir(parents=True, exist_ok=True)
    senado = contracts.find("senado")
    constituicao = contracts.find("constituicao")
    catalogo = {
        "ListaDocumento": {
            "documentos": {
                "documento": [
                    _norma(
                        "1001",
                        "LEI-n",
                        "Lei Numerada",
                        "14999",
                        "Lei nº 14.999 de 28/06/2024",
                        "ALTERA A LEI COMPLEMENTAR X.",
                        "28/06/2024",
                        "LEI-14999-2024-06-28 , Lei do Teste",
                    ),
                    _norma(
                        "1002",
                        "EMC-n",
                        "Emenda Constitucional",
                        "99",
                        "Emenda Constitucional nº 99 de 15/02/2024",
                        "Altera a Constituição.",
                        "15/02/2024",
                        "EMC-99-2024-02-15",
                    ),
                    _norma(
                        "1003",
                        "DEC-n",
                        "Decreto Numerado",
                        "12000",
                        "Decreto nº 12.000 de 01/03/2024",
                        "Regulamenta a Lei X.",
                        "01/03/2024",
                        "DEC-12000-2024-03-01",
                    ),
                ]
            }
        }
    }
    veto = {
        "ListaVetosAnoCN": {
            "Vetos": {
                "Veto": [
                    {
                        "Codigo": "7001",
                        "Materia": {"Codigo": "8001", "Numero": "5", "Ano": "2024", "EmTramitacao": "Não"},
                        "MateriaVetada": {
                            "Codigo": "700",
                            "Sigla": "PLP",
                            "Numero": "700",
                            "Ano": "2023",
                            "Ementa": "ALTERA A LEI COMPLEMENTAR X.",
                            "NormaGerada": {
                                "CodigoNorma": "1001",
                                "NomeNorma": "Lei nº 14.999 de 28/06/2024",
                            },
                        },
                        "Mensagem": {
                            "Sigla": "MSG",
                            "Numero": "300",
                            "Ano": "2024",
                            "UrlPlanalto": "https://www.planalto.gov.br/teste",
                        },
                        "Total": "Não",
                        "Assunto": "Assunto do veto",
                        "DataRecebimentoCongresso": "2024-07-05",
                        "DataPublicacao": "2024-07-01",
                        "DataSobrestacaoPauta": "2024-08-05",
                        "SobrestandoPauta": "Não",
                        "QuantidadeDispositivos": "2",
                    }
                ]
            }
        }
    }
    saida: dict[str, Path] = {}
    arquivos: list[tuple[str, int | None, str, str]] = [
        ("normas", 2024, json.dumps(catalogo), "json"),
        ("vetos", 2024, json.dumps(veto), "json"),
        ("normas_detalhe_constituicao", None, json.dumps(DETALHES[CONSTITUICAO_ID]), "json"),
    ]
    for dataset, ano, texto, extensao in arquivos:
        file = pasta / f"senado-{dataset}-{ano}.{extensao}"
        file.write_text(texto, encoding="utf-8")
        saida[senado.url(dataset, ano)] = file
    for parte, html in (("constituicao", HTML), ("adct", HTML_ADCT)):
        file = pasta / f"{parte}-ec99.html"
        file.write_text(html, encoding="utf-8")
        saida[constituicao.url(parte)] = file
    return saida


def normas_get(url: str) -> tuple[int, bytes]:
    """Substitui as chamadas por item: detalhe da norma, dispositivos de um veto e votos de um dispositivo."""
    for item, detalhe in DETALHES.items():
        if url == f"{BASE}/legislacao/{item}":
            return 200, json.dumps(detalhe).encode()
    for item, dispositivos in DISPOSITIVOS.items():
        if url == f"{BASE}/plenario/resultado/veto/materia/{item}":
            return 200, json.dumps(dispositivos).encode()
    for item, votos in VOTOS.items():
        if url == f"{BASE}/plenario/resultado/veto/dispositivo/{item}":
            return 200, json.dumps(votos).encode()
    return 404, b""
