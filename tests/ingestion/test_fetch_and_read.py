"""Pontos de extensão da ingestão: buscar (HTTP, credenciais, nova tentativa), ler (CSV, JSON) e `custom.py`."""

import gzip
import hashlib
import http.server
import json
import sys
import threading
import time
import types
import urllib.error
from collections.abc import Iterator
from email.message import Message
from pathlib import Path

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import rows
from dado_publico_brasil.ingestion import fetch, loader, read
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract

CUSTOM = "dado_publico_brasil.ingestion.custom.legislativo.federal.teste"
YAML = """
source: teste
power: legislativo
level: federal
access:
  base_url: "http://exemplo"
  format: json
  headers: {{Authorization: "Bearer ${{TOKEN_TESTE}}"}}
datasets:
  votacoes:
    url: "{{base_url}}/votacoes"
    load: full
    write: merge
    records: dados.itens
    primary_key: [id]
    columns: [id, ementa, orgao__sigla, votos]
    nested: [votos]
"""
PAYLOAD = {
    "dados": {
        "itens": [
            {"id": 1, "ementa": "A", "orgao": {"sigla": "PLEN"}, "votos": [{"nome": "X", "voto": "Sim"}]},
            {"id": 2, "ementa": "", "orgao": {"sigla": "CCJ"}, "votos": []},
        ]
    }
}


def source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch | None = None, custom: str | None = None
) -> SourceContract:
    """Declaração de teste; `custom` é o código de um módulo `ingestion/custom/legislativo/federal/teste`."""
    file = tmp_path / "teste.yml"
    file.write_text(YAML.format(), encoding="utf-8")
    if monkeypatch and custom:
        module = types.ModuleType(CUSTOM)
        exec(custom, module.__dict__)  # noqa: S102
        monkeypatch.setitem(sys.modules, CUSTOM, module)
    return load_contract(file)


def landed_json(tmp_path: Path) -> Path:
    file = tmp_path / "votacoes.json"
    file.write_text(json.dumps(PAYLOAD), encoding="utf-8")
    return file


def test_json_reader_follows_the_records_path_and_flattens_objects(tmp_path: Path) -> None:
    contract = source(tmp_path)
    dataset = contract.datasets["votacoes"]
    found = list(read.records(landed_json(tmp_path), contract, dataset))
    assert [r["orgao__sigla"] for r in found] == ["PLEN", "CCJ"]
    assert found[0]["votos"] == [{"nome": "X", "voto": "Sim"}]  # listas seguem para o dlt
    assert read.fields(landed_json(tmp_path), contract, dataset) == ["ementa", "id", "orgao__sigla", "votos"]


def test_json_loads_into_the_raw_with_a_child_table_for_the_list(tmp_path: Path) -> None:
    contract = source(tmp_path)
    settings = Settings(storage_root=tmp_path / "store")
    con = migrations.open_warehouse(settings)
    stats = loader.load_file(settings, contract, contract.datasets["votacoes"], landed_json(tmp_path), 1, con)
    schema = contract.schema
    assert stats == {"read": 2, "filtered": 0, "loaded": 2, "rejected": 0, "conflicting": 0, "replaced": 0}
    parents = rows(con, f"SELECT id, ementa, orgao_sigla FROM {schema}.votacoes ORDER BY id")
    assert [(p["id"], p["ementa"], p["orgao_sigla"]) for p in parents] == [
        ("1", "A", "PLEN"),
        ("2", None, "CCJ"),
    ]
    child = rows(con, f"SELECT nome, voto FROM {schema}.votacoes__votos")
    assert [(c["nome"], c["voto"]) for c in child] == [("X", "Sim")]


def test_custom_module_of_the_source_replaces_reading_and_fetching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = (
        "from pathlib import Path\n"
        "def records(file, dataset):\n    yield {'id': 7, 'ementa': 'do custom'}\n"
        "def download(url, folder):\n    return Path('x'), 'hash', 1\n"
    )
    contract = source(tmp_path, monkeypatch, custom)
    dataset = contract.datasets["votacoes"]
    assert list(read.records(landed_json(tmp_path), contract, dataset)) == [{"id": 7, "ementa": "do custom"}]
    assert fetch.downloader(contract, "votacoes")("u", tmp_path) == (Path("x"), "hash", 1)
    monkeypatch.delitem(sys.modules, CUSTOM)
    assert source(tmp_path).custom is None  # sem módulo próprio: o padrão


def test_credentials_come_from_the_environment_never_from_the_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = source(tmp_path)
    monkeypatch.setenv("TOKEN_TESTE", "segredo")
    assert fetch._request("http://x", contract.headers).get_header("Authorization") == "Bearer segredo"
    monkeypatch.delenv("TOKEN_TESTE")
    with pytest.raises(KeyError):
        fetch._request("http://x", contract.headers)


class Flaky(http.server.BaseHTTPRequestHandler):
    calls = 0

    def do_GET(self) -> None:
        Flaky.calls += 1
        if Flaky.calls < 3:
            self.send_response(503)
            self.end_headers()
            return
        body = json.dumps(PAYLOAD).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def server() -> Iterator[str]:
    Flaky.calls = 0
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Flaky)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/votacoes?de=2024&ate=2024"
    httpd.shutdown()


def test_download_retries_on_server_error_and_keeps_the_original_with_hash(
    server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(time, "sleep", lambda s: None)
    file, digest, size = fetch.download(server, tmp_path, suffix="json")
    assert Flaky.calls == 3
    assert file.name == f"votacoes_de_2024_ate_2024-{digest[:12]}.json"  # nome seguro para URL com consulta
    assert json.loads(file.read_text(encoding="utf-8")) == PAYLOAD and size == file.stat().st_size


def test_client_error_is_definitive_and_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls: list[int] = []

    def not_found() -> None:
        calls.append(1)
        raise urllib.error.HTTPError("u", 404, "Not Found", Message(), None)

    with pytest.raises(urllib.error.HTTPError):
        fetch._retrying(not_found)
    assert calls == [1]


def test_a_null_object_and_a_filled_one_have_the_same_fields(tmp_path: Path) -> None:
    contract = source(tmp_path)
    dataset = contract.datasets["votacoes"]
    file = tmp_path / "v.json"
    file.write_text(json.dumps({"dados": {"itens": [{"id": 1, "orgao": None}]}}), encoding="utf-8")
    nulo = read.fields(file, contract, dataset)
    file.write_text(json.dumps({"dados": {"itens": [{"id": 1, "orgao": {"sigla": "X"}}]}}), encoding="utf-8")
    assert nulo == ["id", "orgao"] and read.fields(file, contract, dataset) == ["id", "orgao__sigla"]


def test_user_agent_carries_the_repository_url_as_contact() -> None:
    request = fetch._request("https://example.org/arquivo.csv", {})
    assert "https://github.com/codigo-publico-brasil/dado-publico-brasil" in (
        request.get_header("User-agent") or ""
    )


class Gzipped(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = gzip.compress(json.dumps(PAYLOAD).encode())
        self.send_response(200)
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


def test_a_response_compressed_in_transport_is_kept_as_the_document_it_carries(tmp_path: Path) -> None:
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Gzipped)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_port}/municipios"
    try:
        file, digest, size = fetch.download(url, tmp_path, suffix="json")
        status, body = fetch.get(url)
    finally:
        httpd.shutdown()
    assert json.loads(file.read_text(encoding="utf-8")) == PAYLOAD and size == file.stat().st_size
    assert digest == hashlib.sha256(file.read_bytes()).hexdigest()  # o hash é do documento, não do transporte
    assert status == 200 and json.loads(body) == PAYLOAD


class Hostile(http.server.BaseHTTPRequestHandler):
    calls = 0

    def do_GET(self) -> None:
        if self.path == "/403":
            self.send_response(403)
            self.end_headers()
        elif self.path in (
            "/short",
            "/flaky",
        ):  # promete 100 bytes e fecha a conexão antes (/flaky: só na 1ª vez)
            Hostile.calls += 1
            full = self.path == "/flaky" and Hostile.calls > 1
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"a" * (100 if full else 40))
            self.close_connection = True
        elif self.path == "/moved":
            self.send_response(302)
            self.send_header(
                "Location",
                "http://" + str(self.headers["Host"]).replace("127.0.0.1", "localhost") + "/ok.csv",
            )
            self.end_headers()
        else:
            body = (
                b"<html>Acesso negado</html>" if self.path in ("/html.zip", "/page.html") else b"a,b\n1,2\n"
            )
            self.send_response(200)
            self.send_header(
                "Content-Type", "text/html" if self.path in ("/html.zip", "/page.html") else "text/csv"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    do_HEAD = do_GET

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def hostile() -> Iterator[str]:
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Hostile)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.mark.parametrize("path", ["/html.zip", "/403", "/moved"])
def test_a_block_is_raised_before_anything_is_written_to_the_landing(
    hostile: str, path: str, tmp_path: Path
) -> None:
    folder = tmp_path / "landing" / "fonte"
    with pytest.raises(fetch.SourceBlocked):
        fetch.download(hostile + path, folder)
    with pytest.raises(fetch.SourceBlocked):
        fetch.head(hostile + path)
    assert not folder.exists() and not folder.parent.exists()


def test_a_source_that_serves_html_as_its_format_is_not_blocked(hostile: str, tmp_path: Path) -> None:
    file, _, _ = fetch.download(hostile + "/page.html", tmp_path, suffix="html")
    assert file.suffix == ".html" and fetch.head(hostile + "/page.html", suffix="html")["size"]


def test_a_subdomain_of_the_same_site_is_not_a_redirect_to_another_host() -> None:
    assert fetch._site("https://www.in.gov.br/x") == fetch._site("https://in.gov.br/y") == "in.gov.br"
    assert fetch._site("https://dadosabertos.camara.leg.br/") == "camara.leg.br"
    assert fetch._site("https://a.example.com/") != fetch._site("https://b.example.org/")


def test_the_courtesy_interval_applies_to_every_request_with_an_injected_clock(
    hostile: str, tmp_path: Path
) -> None:
    now = [0.0]
    pauses: list[float] = []
    pace = fetch.Pace(2, clock=lambda: now[0], sleep=pauses.append)  # 2 por segundo: 0,5 s
    fetch.head(hostile + "/ok.csv", pace=pace)
    now[0] = 0.2
    fetch.download(hostile + "/ok.csv", tmp_path, pace=pace)
    now[0] = 5.0
    fetch.head(hostile + "/ok.csv", pace=pace)
    assert pauses == [pytest.approx(0.3)]


def test_a_redirect_to_another_site_is_accepted_only_when_the_source_declares_it(
    hostile: str, tmp_path: Path
) -> None:
    with pytest.raises(fetch.SourceBlocked):
        fetch.download(hostile + "/moved", tmp_path)
    file, _, _ = fetch.download(hostile + "/moved", tmp_path, sites=("localhost",))
    assert file.read_text(encoding="utf-8") == "a,b\n1,2\n"
    assert fetch.head(hostile + "/moved", sites=("localhost",))["size"]


def test_a_truncated_download_is_retried_and_never_left_in_the_landing(
    hostile: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(time, "sleep", lambda s: None)
    folder = tmp_path / "landing" / "fonte"
    with pytest.raises(OSError, match="truncado"):
        fetch.download(hostile + "/short", folder)
    assert not folder.exists()  # nem o temporário nem a pasta
    Hostile.calls = 0
    file, _, size = fetch.download(hostile + "/flaky", folder)  # a 2ª tentativa vem inteira
    assert size == 100 == file.stat().st_size and [p.name for p in folder.iterdir()] == [file.name]


def test_professions_without_a_title_are_kept_not_rejected_and_the_portal_redirect_is_declared(
    tmp_path: Path,
) -> None:
    from dado_publico_brasil.ingestion import contract as contracts

    camara = contracts.find("camara")
    dataset = camara.datasets["deputadosProfissoes"]
    file = tmp_path / "p.csv"  # a fonte lista o deputado sem profissão com título e data vazios
    file.write_text(
        "uri;id;dataHora;codTipoProfissao;titulo\n"
        "u/1;1;2020-01-01T10:00;5;Médico\nu/1;1;2020-01-01T10:00;5;Médico\nu/2;2;;0;\n",
        encoding="utf-8",
    )
    stats = {"read": 0, "filtered": 0, "loaded": 0, "rejected": 0, "conflicting": 0, "replaced": 0}
    loaded = list(loader.read_rows(file, camara, dataset, 1, stats))
    assert stats["rejected"] == 0 and stats["loaded"] == len(loaded) == 3
    assert contracts.find("transparencia").redirect_sites == ("cgu.gov.br",)
