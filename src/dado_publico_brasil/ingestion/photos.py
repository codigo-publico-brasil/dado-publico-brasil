"""Fotos oficiais dos candidatos: do pacote por UF do landing para uma pasta que se pode servir.

O pacote original continua intacto no landing (com hash). Aqui só se extrai cada imagem para
`<pasta de dados>/fotos/<ano>/<UF>/<SQ_CANDIDATO>.<jpg|jpeg>`, o caminho que
`marts.eleicoes_candidaturas.foto_caminho` indica. É uma cópia derivada: refaz-se do landing quando
quiser, e só se escreve o que falta ou mudou.
"""

import re
import zipfile

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing

MEMBER = re.compile(r"^F?[A-Z]{2}(\d+)_div\.(jpe?g)$")  # o F inicial só existe de 2018 em diante


def extract_all(con: Connection, settings: Settings) -> int:
    """Extrai as fotos dos pacotes vigentes do TSE. Devolve quantas imagens foram escritas."""
    written = 0
    for capture in landing.current_captures(con, "tse"):
        dataset = str(capture["dataset"])
        if not dataset.startswith("fotos_"):
            continue
        folder = (
            settings.storage_root / "fotos" / str(capture["year"]) / dataset.removeprefix("fotos_").upper()
        )
        with zipfile.ZipFile(settings.storage_root / capture["path"]) as package:
            for info in package.infolist():
                found = MEMBER.match(info.filename)
                if not found:
                    continue
                target = folder / f"{found.group(1)}.{found.group(2)}"
                if target.exists() and target.stat().st_size == info.file_size:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(package.read(info))
                written += 1
    return written
