"""Constituição de 1988, texto atualizado da Câmara dos Deputados (`sources/.../constituicao.yml`).

A página `constituicao1988` lista os arquivos HTML atuais e o nome muda a cada emenda
(`ConstituicaoTextoAtualizado_EC 141.html`). `download` lê a página, escolhe o link da parte pedida
(`?parte=constituicao` ou `?parte=adct`) com a emenda mais alta e guarda o arquivo original, sem alterar, como
`<parte>-ec<N>-<hash>.html`. `records` devolve um registro por parágrafo de texto, na ordem do arquivo, sem
interpretá-lo: quem classifica título, artigo, parágrafo, inciso e alínea é o dbt.
"""

import html
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from dado_publico_brasil.ingestion import fetch
from dado_publico_brasil.ingestion.contract import Dataset

LINKS = {
    "constituicao": re.compile(r'href="([^"]*ConstituicaoTextoAtualizado_EC[^"]*\.html)"', re.I),
    "adct": re.compile(r'href="([^"]*adct[^"]*\.html)"', re.I),
}
EMENDA = re.compile(r"ec(?:%20|[ _-])*(\d+)", re.I)
PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def _resolve(url: str) -> tuple[str, str, int]:
    """O link atual da parte pedida na página, a parte e a emenda até a qual o texto está atualizado."""
    parts = urlsplit(url)
    part = parse_qs(parts.query)["parte"][0]
    page = parts._replace(query="", fragment="").geturl()
    status, body = fetch.get(page)
    if status != 200:
        raise RuntimeError(f"página da Constituição respondeu {status}: {page}")
    found = [
        (int(m.group(1)), link)
        for link in LINKS[part].findall(body.decode("utf-8", "replace"))
        if "lixeira" not in link and (m := EMENDA.search(link))
    ]
    if not found:
        raise RuntimeError(f"nenhum arquivo HTML de '{part}' na página {page}")
    amendment, link = max(found)
    return urljoin(page, link), part, amendment


def download(url: str, folder: Path) -> tuple[Path, str, int]:
    link, part, amendment = _resolve(url)
    file, digest, size = fetch.download(link, folder, suffix="html")
    target = folder / f"{part}-ec{amendment}-{digest[:12]}.html"
    if target.exists():
        file.unlink()
    else:
        file.rename(target)
    return target, digest, size


def head(url: str) -> dict[str, str | None]:
    return fetch.head(_resolve(url)[0])


def records(file: Path, dataset: Dataset) -> Iterator[dict[str, Any]]:
    amendment = re.search(r"-ec(\d+)-", file.name)
    order = 0
    for paragraph in PARAGRAPH.findall(file.read_text(encoding="utf-8", errors="replace")):
        line = re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", paragraph))).strip()
        if line:
            order += 1
            yield {
                "ordem": order,
                "linha": line,
                "emenda_do_arquivo": amendment.group(1) if amendment else None,
            }
