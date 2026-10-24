"""Dataset por item: lotes com envelope, retomada, versão, falhas, auditoria e leitura no raw."""

import gzip
import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import batch, foreach, loader
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract

YAML = """
source: teste
power: legislativo
level: municipal
access: {base_url: "BASE", format: csv, rate_limit: 1000}
datasets:
  pais:
    url: "{base_url}/pais.csv"
    load: full
    write: replace
    columns: [id, tipo, data, versao]
  filhos:
    url: "{base_url}/pais/{item}/filhos"
    load: foreach
    format: json
    headers: {Accept: application/json}
    records: dados
    write: merge
    foreach: {from: pais, item: id, where: "tipo = 'PL'", recent_by: data, version: versao, batch_size: 2}
    primary_key: [_item, seq]
    columns: [_item, seq, texto]
"""
PAIS = [  # id, tipo, data, versao
    ("1", "PL", "2020-01-01", "a"),
    ("2", "PL", "2022-01-01", "a"),
    ("3", "PL", "2024-01-01", "a"),
    ("4", "REQ", "2025-01-01", "a"),  # fora do `where`
    ("5", "PL", "2023-01-01", "a"),
]
Env = tuple[Connection, Settings, SourceContract]


class Handler(http.server.BaseHTTPRequestHandler):
    calls: list[str] = []
    broken = {"3"}  # responde 503

    def do_GET(self) -> None:
        item = self.path.split("/")[2]
        Handler.calls.append(item)
        if item in Handler.broken:
            self.send_response(503)
            self.end_headers()
            return
        if item == "5":
            self.send_response(404)
            self.end_headers()
            return
        dados = [{"seq": 1, "texto": f"t{item}"}, {"seq": 2, "texto": f"u{item}"}]
        body = json.dumps({"dados": dados}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def base(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    Handler.calls = []
    Handler.broken = {"3"}
    monkeypatch.setattr("time.sleep", lambda s: None)  # nova tentativa sem espera
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.fixture
def env(base: str, tmp_path: Path) -> Env:
    file = tmp_path / "teste.yml"
    file.write_text(YAML.replace("BASE", base), encoding="utf-8")
    contract = load_contract(file)
    settings = Settings(storage_root=tmp_path / "store")
    con = migrations.open_warehouse(settings)
    con.execute(f"CREATE SCHEMA {contract.schema}")
    con.execute(
        f"CREATE TABLE {contract.schema}.pais (id VARCHAR, tipo VARCHAR, data VARCHAR, versao VARCHAR)"
    )
    con.executemany(f"INSERT INTO {contract.schema}.pais VALUES (?, ?, ?, ?)", PAIS)
    return con, settings, contract


def latest(con: Connection) -> dict[str, int]:
    found = rows(con, "SELECT item, status FROM metadata.capture_items ORDER BY id")
    return {r["item"]: r["status"] for r in found}


def test_most_recent_items_first_within_the_filter_and_limit(env: Env) -> None:
    con, settings, contract = env
    done = foreach.capture(con, settings, contract, "filhos", limit=2)
    assert done == 2
    # 2024 e 2023 primeiro (o 503 do 3 é tentado 3 vezes); o REQ de 2025 está fora do `where`
    assert Handler.calls == ["3", "3", "3", "5"]
    assert scalar(con, "SELECT COUNT(*) FROM metadata.captures WHERE dataset = 'filhos'") == 1  # um lote


def test_resuming_continues_with_what_is_missing_and_never_repeats_what_is_done(env: Env) -> None:
    con, settings, contract = env
    foreach.capture(con, settings, contract, "filhos", limit=2)  # 3 (falha) e 5 (404)
    Handler.calls.clear()
    Handler.broken.clear()
    foreach.capture(con, settings, contract, "filhos")
    # o 404 não se repete; a falha do 3 é tentada de novo; faltam o 2 e o 1
    assert Handler.calls == ["3", "2", "1"]
    assert latest(con) == {"3": 200, "5": 404, "2": 200, "1": 200}
    Handler.calls.clear()
    assert foreach.capture(con, settings, contract, "filhos") == 0 and Handler.calls == []


def test_a_changed_version_fetches_the_item_again(env: Env) -> None:
    con, settings, contract = env
    Handler.broken.clear()
    foreach.capture(con, settings, contract, "filhos")
    con.execute(f"UPDATE {contract.schema}.pais SET versao = 'b' WHERE id = '2'")
    Handler.calls.clear()
    foreach.capture(con, settings, contract, "filhos")
    assert Handler.calls == ["2"]


def test_each_answer_is_kept_byte_for_byte_and_indexed(env: Env) -> None:
    con, settings, contract = env
    foreach.capture(con, settings, contract, "filhos", limit=1)
    path = rows(con, "SELECT path FROM metadata.captures WHERE dataset = 'filhos'")[0]["path"]
    [envelope] = list(batch.read(settings.storage_root / path))
    assert envelope["item"] == "3" and envelope["status"] == 503 and envelope["corpo"] == ""
    assert gzip.open(settings.storage_root / path).read().count(b"\n") == 1
    Handler.broken.clear()
    foreach.capture(con, settings, contract, "filhos", limit=1)
    ok = rows(con, "SELECT sha256 FROM metadata.capture_items WHERE status = 200")[0]["sha256"]
    path = rows(con, "SELECT path FROM metadata.captures WHERE dataset = 'filhos' ORDER BY id DESC")[0][
        "path"
    ]
    [envelope] = list(batch.read(settings.storage_root / path))
    assert envelope["sha256"] == ok and json.loads(envelope["corpo"])["dados"][0]["texto"] == "t3"


def test_batches_load_into_the_raw_with_the_item_and_skip_failed_answers(env: Env) -> None:
    con, settings, contract = env
    foreach.capture(con, settings, contract, "filhos")  # 3 falha, 5 é 404, 2 e 1 respondem
    captures, _ = loader.load_pending(con, settings, contract)
    assert captures == 2  # dois lotes de dois itens
    found = rows(con, f"SELECT _item, seq, texto FROM {contract.schema}.filhos ORDER BY _item, seq")
    assert [(r["_item"], r["seq"], r["texto"]) for r in found] == [
        ("1", "1", "t1"),
        ("1", "2", "u1"),
        ("2", "1", "t2"),
        ("2", "2", "u2"),
    ]


def test_verify_finds_a_changed_file_and_a_changed_answer(env: Env) -> None:
    con, settings, contract = env
    Handler.broken.clear()
    foreach.capture(con, settings, contract, "filhos", limit=2)
    assert foreach.verify(con, settings) == []
    path = settings.storage_root / rows(con, "SELECT path FROM metadata.captures ORDER BY id")[0]["path"]
    envelopes = list(batch.read(path))
    envelopes[0]["corpo"] = envelopes[0]["corpo"].replace("t3", "XX")
    batch.write(path, envelopes)  # adultera o corpo e refaz o arquivo
    problems = foreach.verify(con, settings)
    assert any("mudou depois da captura" in p for p in problems)


def test_coverage_counts_obtained_missing_and_failed_items(env: Env) -> None:
    con, settings, contract = env
    foreach.capture(con, settings, contract, "filhos", limit=3)
    assert foreach.coverage(con, contract, "filhos") == {
        "esperados": 4,
        "obtidos": 1,
        "inexistentes": 1,
        "falhas": 1,
        "faltam": 2,
    }
    check = rows(con, "SELECT status, detail FROM metadata.source_checks WHERE check_name = 'coverage'")[0]
    assert check["status"] == "warn" and "falhas 1" in check["detail"]


def test_foreach_needs_item_in_the_url_and_the_item_column_in_the_key(tmp_path: Path) -> None:
    text = YAML.replace("BASE", "http://x").replace("/pais/{item}/filhos", "/filhos")
    file = tmp_path / "ruim.yml"
    file.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="foreach exige"):
        load_contract(file)


def test_a_dataset_whose_source_has_not_been_loaded_yet_has_no_items_instead_of_failing(env: Env) -> None:
    con, _, contract = env
    con.execute(f"DROP TABLE {contract.schema}.pais")  # o raw da origem ainda não existe: não há o que buscar
    assert foreach.pending(con, contract, "filhos") == []
    assert foreach.coverage(con, contract, "filhos") == {
        "esperados": 0,
        "obtidos": 0,
        "inexistentes": 0,
        "falhas": 0,
        "faltam": 0,
    }
