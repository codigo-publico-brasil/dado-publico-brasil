"""Materializa os arquivos de um dataset (bloco `arquivos` do contrato) para servir ao público (ADR 0037).

Para cada captura vigente, copia o arquivo ou extrai os membros do zip que casam com `membro`, para
`<pasta de dados>/arquivos/<poder>/<esfera>/<fonte>/arq_<collection>/<path>`, e anota em `metadata.arquivos`
o hash e a captura de origem. É cópia derivada do landing (que fica intacto): refaz-se quando quiser, e só se
escreve o que falta ou mudou (gravação atômica; membro já presente com o mesmo tamanho não é regravado).
Captura corrompida ou caminho que sai da coleção vira aviso e não para as outras. Membro que some de uma
captura nova não é apagado: a última cópia fica, com a captura de origem anterior.
O `export` lê esta pasta e publica o que o contrato manda (`publish: true`).
"""

import hashlib
import re
import shutil
import warnings
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows
from dado_publico_brasil.ingestion.contract import Files, SourceContract

HASH_SUFFIX = re.compile(r"-[0-9a-f]{12}(?=\.[^.]+$)")  # o landing põe o hash no nome do arquivo
Member = tuple[str, int, Callable[[Path], None], str | None]  # caminho, bytes, grava, sha256 se já se sabe


def folder(settings: Settings, contract: SourceContract, colecao: str) -> Path:
    base = settings.storage_root / "arquivos" / contract.power / contract.level / contract.source
    return base / f"arq_{colecao}"


def materialize(con: Connection, settings: Settings, contract: SourceContract) -> int:
    """Materializa as capturas vigentes dos datasets com `arquivos`. Devolve quantos arquivos escreveu."""
    written = 0
    for dataset in (d for d in contract.datasets.values() if d.files):
        spec = dataset.files
        assert spec is not None
        base = folder(settings, contract, spec.collection)
        known = {
            r["caminho"]: r
            for r in rows(
                con,
                "SELECT caminho, id_captura, qtd_bytes, sha256_arquivo FROM metadata.arquivos "
                "WHERE fonte = ? AND colecao = ?",
                (contract.source, spec.collection),
            )
        }
        for capture in rows(
            con,
            "SELECT * FROM metadata.capturas c WHERE fonte = ? AND dataset = ? AND id_captura = "
            "(SELECT MAX(id_captura) FROM metadata.capturas WHERE url = c.url) ORDER BY id_captura",
            (contract.source, dataset.name),
        ):
            source = settings.storage_root / capture["caminho"]
            if not source.exists():
                continue
            try:
                written += _capture(con, contract, spec, dataset.name, capture, source, base, known)
            except (zipfile.BadZipFile, ValueError, OSError) as error:  # uma captura ruim não para as outras
                warnings.warn(
                    f"{contract.source}.{dataset.name} captura {capture['id_captura']}: {error}", stacklevel=2
                )
    return written


def _capture(
    con: Connection,
    contract: SourceContract,
    spec: Files,
    dataset: str,
    capture: dict[str, Any],
    source: Path,
    base: Path,
    known: dict[str, Any],
) -> int:
    """Materializa os arquivos de uma captura (gravação atômica: temporário e rename). Devolve quantos."""
    written = 0
    for name, size, write, sha in _members(spec, dataset, capture, source):
        target = base / name
        if base.resolve() not in target.resolve().parents:
            raise ValueError(f"caminho '{name}' sai da coleção")
        old = known.get(name)
        current = old and old["id_captura"] == capture["id_captura"] and old["qtd_bytes"] == size
        if target.exists() and target.stat().st_size == size and current:
            continue
        # mesmo tamanho já materializado (captura nova do mesmo membro): não regrava, só reaponta
        same = (
            target.exists() and target.stat().st_size == size and old is not None and old["qtd_bytes"] == size
        )
        if not same:
            target.parent.mkdir(parents=True, exist_ok=True)
            part = target.with_name(target.name + ".parte")
            try:
                write(part)
                part.replace(target)
            finally:
                part.unlink(missing_ok=True)
        con.execute(
            "INSERT INTO metadata.arquivos (fonte, colecao, caminho, dataset, id_captura, "
            "sha256_arquivo, qtd_bytes, fl_original) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (fonte, colecao, caminho) "
            "DO UPDATE SET dataset = excluded.dataset, id_captura = excluded.id_captura, "
            "sha256_arquivo = excluded.sha256_arquivo, qtd_bytes = excluded.qtd_bytes, "
            "fl_original = excluded.fl_original",
            (
                contract.source,
                spec.collection,
                name,
                dataset,
                capture["id_captura"],
                sha
                or (
                    old and old["sha256_arquivo"] if same else hashlib.sha256(target.read_bytes()).hexdigest()
                ),
                size,
                spec.member is None,
            ),
        )
        written += not same
    return written


def _members(spec: Files, dataset: str, capture: dict[str, Any], source: Path) -> list[Member]:
    """Os arquivos que a captura gera: ela mesma (sem `member`) ou cada membro do zip que casa."""
    fields = {"dataset": dataset, "partition": capture["particao"]}
    if spec.member is None:
        name = spec.path.format(**fields, name=HASH_SUFFIX.sub("", source.name))
        return [(name, source.stat().st_size, lambda t: _copy(source, t), capture["sha256"])]
    pattern, found = re.compile(spec.member), list[Member]()
    with zipfile.ZipFile(source) as package:
        for info in package.infolist():
            if match := pattern.match(info.filename):
                name = spec.path.format(**fields, name=Path(info.filename).name, **match.groupdict())
                found.append((name, info.file_size, _extract(source, info.filename), None))
    return found


def _copy(source: Path, target: Path) -> None:
    shutil.copyfile(source, target)


def _extract(source: Path, member: str) -> Callable[[Path], None]:
    def write(target: Path) -> None:
        with zipfile.ZipFile(source) as package:
            target.write_bytes(package.read(member))

    return write
