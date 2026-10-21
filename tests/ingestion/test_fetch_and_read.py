"""Pontos de extensão da ingestão: buscar (HTTP, credenciais, nova tentativa), ler (CSV, JSON) e `custom.py`."""

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

from plataforma_dados.core import migrations
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import rows
from plataforma_dados.ingestion import fetch, loader, read
from plataforma_dados.ingestion.contract import SourceContract, load_contract

CUSTOM = "plataforma_dados.ingestion.custom.legislativo.federal.teste"
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
    assert stats == {"read": 2, "loaded": 2, "rejected": 0}
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
    assert fetch.downloader(contract)("u", tmp_path) == (Path("x"), "hash", 1)
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
