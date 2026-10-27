"""Respostas sintéticas das APIs por item (tramitação da Câmara, processo do Senado); sem rede."""

import json

CAMARA = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{}/tramitacoes"
SENADO = "https://legis.senado.leg.br/dadosabertos/processo/{}"


def _andamento(seq: int, hora: str, orgao: str, situacao: str, despacho: str) -> dict[str, object]:
    return {
        "sequencia": seq,
        "dataHora": hora,
        "siglaOrgao": orgao,
        "regime": "Ordinária",
        "descricaoTramitacao": "Despacho" if seq > 1 else "Apresentação de Proposição",
        "codTipoTramitacao": "100",
        "descricaoSituacao": situacao,
        "codSituacao": 1140,
        "despacho": despacho,
        "ambito": "Regimental",
        "apreciacao": "Conclusiva",
        "uriOrgao": "https://exemplo/orgaos/4",
        "url": None,
    }


def _camara_corpo(item: str) -> bytes:
    dados = [
        _andamento(
            1, "2024-03-01T10:00", "MESA", "AGUARDANDO DESIGNAÇÃO", f"Apresentação da proposição {item}."
        ),
        _andamento(2, "2024-03-05T09:30", "CCJC", "AGUARDANDO PARECER", "Às Comissões."),
        _andamento(3, "2025-02-02T09:30", "PLEN", "TRANSFORMADO EM NORMA JURÍDICA", "Sancionada."),
    ]
    return json.dumps({"dados": dados, "links": [{"rel": "self", "href": CAMARA.format(item)}]}).encode()


def _senado_corpo() -> bytes:
    processo = {
        "id": 1,
        "codigoMateria": 700,
        "identificacao": "PLP 700/2023",
        "sigla": "PLP",
        "numero": "700",
        "ano": 2023,
        "tramitando": "Não",
        "situacaoAtual": "TRANSFORMADA EM NORMA JURÍDICA",
        "siglaSituacaoAtual": "TRNJ",
        "dataSituacaoAtual": "2024-07-01",
        "dataInicioEfetivo": "2023-05-02",
        "siglaCasaIniciadora": "SF",
        "normaGerada": {
            "codigo": 99,
            "siglaTipo": "LCP",
            "tipo": "Lei Complementar",
            "numero": 220,
            "anoAssinatura": "2024",
            "dataAssinatura": "2024-06-28",
            "dataPublicacao": "2024-07-01",
            "descricao": "Lei Complementar nº 220 de 28/06/2024",
            "siglaVeiculoPublicacao": "DOU",
        },
        "autoriaIniciativa": [{"autor": "Beto Barreiras", "codigoParlamentar": 5000, "siglaTipo": "SENADOR"}],
        "autuacoes": [{"numero": 1, "informesLegislativos": []}],
    }
    return json.dumps(processo).encode()


def _detalhe(codigo: str, civil: str, nascimento: str, foto: str) -> bytes:
    corpo = {
        "DetalheParlamentar": {
            "Parlamentar": {
                "IdentificacaoParlamentar": {
                    "CodigoParlamentar": codigo,
                    "NomeCompletoParlamentar": civil,
                    "UrlFotoParlamentar": foto,
                    "EmailParlamentar": "sen.exemplo@senado.leg.br",
                    "UrlPaginaParlamentar": "http://senado/perfil/" + codigo,
                },
                "Telefones": {
                    "Telefone": [
                        {"NumeroTelefone": "33036777", "OrdemPublicacao": "1"},
                        {"NumeroTelefone": "33036568", "OrdemPublicacao": "2"},
                    ]
                },
                "DadosBasicosParlamentar": {
                    "DataNascimento": nascimento,
                    "Naturalidade": "Santos",
                    "UfNaturalidade": "SP",
                    "EnderecoParlamentar": "Anexo 2, gabinete 5",
                },
            }
        }
    }
    return json.dumps(corpo).encode()


DETALHES = {
    "5000": ("Roberto Barreiras", "1970-05-05", "http://foto/s5000.jpg"),
    "5001": ("Ana Aparecida da Silva", "1975-06-06", "http://foto/s5001.jpg"),
    "5003": ("Bia Souza", "1990-01-01", "http://foto/s5003.jpg"),
}


def _deputado(item: str) -> bytes:
    """Cadastro do deputado: CPF e e-mail pessoal vêm na resposta e nunca devem entrar no raw."""
    corpo = {
        "dados": {
            "id": int(item),
            "cpf": "11122233344",
            "escolaridade": "SUPERIOR",
            "ultimoStatus": {
                "nomeEleitoral": "Ana Árvore",
                "siglaPartido": "AAA",
                "siglaUf": "SP",
                "idLegislatura": 57,
                "email": "pessoal@exemplo.com",
                "urlFoto": "http://foto/d.jpg",
                "situacao": "Exercício",
                "condicaoEleitoral": "Titular",
                "data": "2023-02-01",
                "gabinete": {
                    "nome": "979",
                    "predio": "3",
                    "sala": "979",
                    "andar": None,
                    "telefone": "3215-5979",
                    "email": "dep.ana@camara.leg.br",
                },
            },
        },
        "links": [],
    }
    return json.dumps(corpo).encode()


def _historico(item: str) -> bytes:
    """Histórico do deputado: início da legislatura, posse e uma licença; o e-mail e a foto não devem entrar."""
    base = {
        "id": int(item),
        "nome": "Ana Árvore",
        "nomeEleitoral": "ANA ÁRVORE",
        "siglaPartido": "AAA",
        "siglaUf": "SP",
        "idLegislatura": 57,
        "email": "nao.entra@exemplo.gov.br",
        "urlFoto": "http://foto/d.jpg",
        "condicaoEleitoral": "Titular",
    }
    dados = [
        {
            **base,
            "dataHora": "2023-02-01T00:00",
            "situacao": None,
            "descricaoStatus": "Nome no início da legislatura",
        },
        {
            **base,
            "dataHora": "2023-02-03T12:05",
            "situacao": "Exercício",
            "descricaoStatus": "Entrada - Posse",
        },
        {
            **base,
            "dataHora": "2024-03-01T09:00",
            "situacao": "Licença",
            "descricaoStatus": "Saída - Afastamento",
        },
    ]
    return json.dumps({"dados": dados, "links": []}).encode()


def fake_get(url: str) -> tuple[int, bytes]:
    """Substitui a chamada à API: 100 e 101 têm tramitação, 102 não existe na fonte (404)."""
    for item in ("100", "101"):
        if url == CAMARA.format(item):
            return 200, _camara_corpo(item)
    if url == "https://dadosabertos.camara.leg.br/api/v2/deputados/10":
        return 200, _deputado("10")
    if url == "https://dadosabertos.camara.leg.br/api/v2/deputados/10/historico":
        return 200, _historico("10")
    if url == SENADO.format("1"):
        return 200, _senado_corpo()
    for codigo, (civil, nascimento, foto) in DETALHES.items():
        if url == f"https://legis.senado.leg.br/dadosabertos/senador/{codigo}":
            return 200, _detalhe(codigo, civil, nascimento, foto)
    return 404, b""
