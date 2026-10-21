"""Dados sintéticos no formato real da Câmara (CSV com ponto e vírgula, aspas e BOM); sem rede.

O conjunto tem: 3 pessoas (duas no cadastro, uma só nos votos), 3 proposições carregadas (uma com
ementa toda em maiúsculas) e uma autoria de proposição não carregada, 2 votações e 4 votos.
"""

import csv
import hashlib
from collections.abc import Callable
from pathlib import Path

from plataforma_dados.ingestion import contract as contracts

BASE = "https://dadosabertos.camara.leg.br/api/v2"


def write_csv(caminho: Path, colunas: list[str], linhas: list[list[str]]) -> Path:
    """CSV no formato da Câmara: ponto e vírgula, aspas, UTF-8 com BOM."""
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        escritor.writerow(colunas)
        escritor.writerows(linhas)
    return caminho


def fake_downloader(arquivos: dict[str, Path]) -> Callable[[str, Path], tuple[Path, str, int]]:
    """Substitui o download: copia o arquivo de teste para o bruto, com hash no nome."""

    def baixar(url: str, pasta: Path) -> tuple[Path, str, int]:
        origem = arquivos[url]
        conteudo = origem.read_bytes()
        hash_hex = hashlib.sha256(conteudo).hexdigest()
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{origem.stem}-{hash_hex[:12]}{origem.suffix}"
        destino.write_bytes(conteudo)
        return destino, hash_hex, len(conteudo)

    return baixar


def no_headers(url: str) -> dict[str, str | None]:
    """Substitui a pergunta à fonte: sem rede, a fonte nunca informa cabeçalhos."""
    return {}


def synthetic_files(pasta: Path) -> dict[str, Path]:
    """Os arquivos sintéticos, por URL oficial (como o extrator os pede)."""
    pasta.mkdir(parents=True, exist_ok=True)
    contract = contracts.find("camara")
    url_do_conjunto = contract.url

    def arquivo(conjunto: str, ano: int | None) -> Path:
        return pasta / url_do_conjunto(conjunto, ano).rsplit("/", 1)[-1]

    saida: dict[str, Path] = {}

    def guardar(conjunto: str, ano: int | None, colunas: str, linhas: list[list[str]]) -> None:
        caminho = write_csv(arquivo(conjunto, ano), colunas.split(), linhas)
        saida[url_do_conjunto(conjunto, ano)] = caminho

    guardar(
        "deputados",
        None,
        "uri nome idLegislaturaInicial idLegislaturaFinal nomeCivil cpf siglaSexo urlRedeSocial "
        "urlWebsite dataNascimento dataFalecimento ufNascimento municipioNascimento",
        [
            [f"{BASE}/deputados/10", "ANA ÁRVORE", "56", "57", "ANA DA SILVA", "12345678900", "F"]
            + ["http://rede", "http://site", "1980-02-03", "", "SP", "Santos"],
            [f"{BASE}/deputados/11", "Bia", "57", "57", "BIA SOUZA", "", "F"]
            + ["", "", "1990-01-01", "", "RJ", "Niterói"],
        ],
    )
    guardar(
        "deputadosProfissoes",
        None,
        "uri id dataHora codTipoProfissao titulo",
        [
            [f"{BASE}/deputados/10", "10", "2026-01-01T10:00:00", "5", "ADVOGADA"],
            [f"{BASE}/deputados/11", "11", "", "0", ""],
        ],
    )
    guardar(
        "deputadosOcupacoes",
        None,
        "id uri titulo entidade entidadeUF entidadePais anoInicio anoFim",
        [["10", "", "Diretora", "Entidade X", "SP", "BRASIL", "2010", "2015"]],
    )
    guardar(
        "proposicoes",
        2024,
        "id siglaTipo numero ano descricaoTipo ementa dataApresentacao urlInteiroTeor "
        "ultimoStatus_dataHora ultimoStatus_siglaOrgao ultimoStatus_descricaoSituacao "
        "ultimoStatus_descricaoTramitacao ultimoStatus_regime ultimoStatus_apreciacao",
        [
            ["100", "PEC", "5", "2024", "Proposta", "Ementa A.", "2024-03-01T10:00", ""]
            + ["2025-02-02T09:30", "CCJC", "Aguardando Parecer", "Recebimento", "Especial"]
            + ["Plenário"],
            ["101", "PL", "7", "2025", "Projeto", "Ementa B.", "2025-06-01T09:00", ""]
            + ["2025-12-01T10:00", "MESA", "Arquivada", "", "", ""],
            ["102", "PL", "9", "2019", "Projeto", "REQUER O DESARQUIVAMENTO DE PROPOSIÇÕES."]
            + ["2019-01-10T08:00", "", "", "", "", "", "", ""],
        ],
    )
    cabecalho_autor = (
        "idProposicao uriProposicao idDeputadoAutor uriAutor codTipoAutor tipoAutor nomeAutor "
        "siglaPartidoAutor uriPartidoAutor siglaUFAutor ordemAssinatura proponente"
    )

    def autor(prop: str, id_dep: str, tipo: str, nome: str, ordem: str, proponente: str) -> list[str]:
        return [prop, "", id_dep, "", "10000", tipo, nome, "AAA", "", "SP", ordem, proponente]

    guardar(
        "proposicoesAutores",
        2024,
        cabecalho_autor,
        [
            autor("100", "10", "Deputado(a)", "ANA ÁRVORE", "1", "1"),
            autor("100", "11", "Deputado(a)", "Bia", "2", "0"),
            autor("100", "", "ÓRGÃO DO PODER LEGISLATIVO", "SENADO FEDERAL", "3", "0"),
            autor("101", "10", "Deputado(a)", "ANA ÁRVORE", "1", "1"),
            autor("101", "11", "Deputado(a)", "Bia", "2", "0"),
            autor("102", "10", "Deputado(a)", "ANA ÁRVORE", "1", "1"),
            autor("999", "10", "Deputado(a)", "ANA ÁRVORE", "1", "1"),
        ],
    )
    guardar(
        "votacoes",
        2024,
        "id uri data dataHoraRegistro idOrgao uriOrgao siglaOrgao idEvento uriEvento aprovacao "
        "votosSim votosNao votosOutros descricao",
        [
            ["100-1", "", "2024-05-01", "2024-05-01T20:00:00", "180", "", "PLEN", "9", "", "1"]
            + ["2", "1", "0", "Aprovada a PEC."],
            ["101-1", "", "2025-07-01", "2025-07-01T18:00:00", "180", "", "PLEN", "9", "", "0"]
            + ["1", "1", "0", "Rejeitado o PL."],
        ],
    )

    def voto(vot: str, hora: str, escolha: str, id_dep: str, nome: str, partido: str) -> list[str]:
        return [vot, "", hora, escolha, id_dep, "", nome, partido]

    def com_partido(linha: list[str], id_partido: str, uf: str, foto: str) -> list[str]:
        return [*linha, f"{BASE}/partidos/{id_partido}", uf, "57", foto]

    guardar(
        "votacoesVotos",
        2024,
        "idVotacao uriVotacao dataHoraVoto voto deputado_id deputado_uri deputado_nome "
        "deputado_siglaPartido deputado_uriPartido deputado_siglaUf deputado_idLegislatura "
        "deputado_urlFoto",
        [
            com_partido(
                voto("100-1", "2024-05-01T20:01:00", "Sim", "10", "Ana Árvore", "AAA"),
                "1",
                "SP",
                "http://foto/10.jpg",
            ),
            com_partido(
                voto("101-1", "2025-07-01T18:00:00", "Não", "10", "Ana Árvore", "BBB"),
                "2",
                "SP",
                "http://foto/10.jpg",
            ),
            com_partido(voto("100-1", "2024-05-01T20:02:00", "Sim", "11", "Bia", "BBB"), "2", "RJ", ""),
            com_partido(voto("100-1", "2024-05-01T20:03:00", "Não", "12", "CAIO", "AAA"), "1", "MG", ""),
        ],
    )
    guardar(
        "votacoesOrientacoes",
        2024,
        "idVotacao uriVotacao siglaOrgao descricao siglaBancada uriBancada orientacao",
        [
            ["100-1", "", "PLEN", "d", "Governo", "", "Sim"],
            ["100-1", "", "PLEN", "d", "Bl X", "", "Não"],
        ],
    )
    guardar(
        "votacoesProposicoes",
        2024,
        "idVotacao uriVotacao data descricao proposicao_id proposicao_uri proposicao_titulo "
        "proposicao_ementa proposicao_codTipo proposicao_siglaTipo proposicao_numero "
        "proposicao_ano",
        [["100-1", "", "2024-05-01", "d", "100", "", "PEC 5/2024", "e", "136", "PEC", "5", "2024"]],
    )
    guardar(
        "votacoesObjetos",
        2024,
        "idVotacao uriVotacao data descricao proposicao_id proposicao_uri proposicao_ementa "
        "proposicao_codTipo proposicao_siglaTipo proposicao_numero proposicao_ano "
        "proposicao_titulo",
        [["100-1", "", "2024-05-01", "d", "100", "", "e", "136", "PEC", "5", "2024", "PEC 5/2024"]],
    )
    guardar(
        "legislaturas",
        None,
        "idLegislatura dataInicio dataFim anoEleicao",
        [["56", "2019-02-01", "2023-01-31", "2018"], ["57", "2023-02-01", "2027-01-31", "2022"]],
    )
    guardar("partidos", None, "id sigla nome", [["1", "AAA", "PARTIDO AAA"], ["2", "BBB", "Partido BBB"]])
    guardar(
        "orgaos",
        None,
        "uri sigla apelido nome codTipoOrgao tipoOrgao dataInicio dataInstalacao dataFim "
        "descricaoSituacao casa",
        [
            [f"{BASE}/orgaos/4", "MESA", "Mesa Diretora", "Mesa Diretora da Câmara", "1", "Comissão Diretora"]
            + ["", "", "", "", "", "Câmara dos Deputados"],
            [f"{BASE}/orgaos/180", "PLEN", "Plenário", "Plenário", "26", "Plenário Virtual"]
            + ["2020-03-20T00:00:00", "2020-03-20T00:00:00", "", "3", "CONSTITUÍDA", ""],
        ],
    )
    cabecalho_membro = (
        "uriOrgao siglaOrgao uriDeputado nomeDeputado siglaPartido siglaUF cargo dataInicio dataFim"
    )
    guardar(
        "orgaosDeputados",
        57,
        cabecalho_membro,
        [
            [f"{BASE}/orgaos/4", "MESA", f"{BASE}/deputados/10", "Ana Árvore", "AAA", "SP"]
            + ["Presidente", "2023-02-01", ""],
            [f"{BASE}/orgaos/4", "MESA", f"{BASE}/deputados/10", "Ana Árvore", "AAA", "SP"]
            + ["Presidente", "2023-02-01", "2025-02-01"],
            [f"{BASE}/orgaos/180", "PLEN", f"{BASE}/deputados/11", "Bia", "BBB", "RJ"]
            + ["Titular", "2024-01-01", ""],
            [f"{BASE}/orgaos/180", "PLEN", f"{BASE}/deputados/99", "Zed", "CCC", "MG"]
            + ["Titular", "2024-01-01", ""],
        ],
    )
    guardar(
        "frentes",
        None,
        "id titulo dataCriacao idLegislatura situacao coordenador_id",
        [["500", "Frente X", "2023-03-01", "57", "EM ANDAMENTO", "10"]],
    )
    guardar(
        "frentesDeputados",
        None,
        "id deputado_.id deputado_.idLegislatura deputado_.urlFoto deputado_.codTitulo deputado_.titulo "
        "dataInicio dataFim",
        [
            ["500", "10", "57", "http://foto/10.jpg", "14", "Coordenador", "", ""],
            ["500", "11", "57", "http://foto/11.jpg", "1004", "Membro", "", ""],
            ["500", "98", "57", "", "1004", "Membro", "", ""],
        ],
    )
    return saida
