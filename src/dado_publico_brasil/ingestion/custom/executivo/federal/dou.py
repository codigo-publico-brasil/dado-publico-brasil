"""Diário Oficial da União, arquivos XML mensais da Imprensa Nacional (`sources/.../dou.yml`).

A página de dados abertos lista, para cada mês (`?ano=2026&mes=Outubro`), um zip por seção. O nome muda a cada
atualização no mês corrente (`S01102026_Atualizado185748.zip`) e é fixo nos meses fechados (`S01082026.zip`).
`download` lê a página do mês, acha o link da seção pedida (`?ano=AAAAMM&secao=1`) e guarda o zip original,
sem alterar, com o nome da Imprensa e o hash. A página só responde se o pedido traz `Accept: */*`.
"""

import html
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dado_publico_brasil.ingestion import fetch

MONTHS = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)
HEADERS = {"Accept": "*/*"}


def _resolve(url: str) -> tuple[str, str]:
    """O link atual do zip da seção no mês, e o nome do arquivo."""
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    year, month = divmod(int(query["ano"][0]), 100)
    section = int(query["secao"][0])
    page = parts._replace(query=f"ano={year}&mes={MONTHS[month - 1]}", fragment="").geturl()
    status, body = fetch.get(page, HEADERS)
    if status != 200:
        raise RuntimeError(f"página do DOU respondeu {status}: {page}")
    link = re.search(
        rf"https://www\.in\.gov\.br/documents/[\w/-]+/(S{section:02d}{month:02d}{year}(?:_[\w-]+)?\.zip)/[^\s\"'<>]*",
        html.unescape(body.decode("utf-8", "replace")),
    )
    if link is None:
        raise RuntimeError(f"nenhum zip da seção {section} em {MONTHS[month - 1]} de {year}: {page}")
    return link.group(0), link.group(1)


def download(url: str, folder: Path) -> tuple[Path, str, int]:
    link, name = _resolve(url)
    return fetch.download(link, folder, HEADERS, "zip", name)


def head(url: str) -> dict[str, str | None]:
    return fetch.head(_resolve(url)[0], HEADERS)
