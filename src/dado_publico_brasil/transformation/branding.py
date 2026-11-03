"""Identidade do Dado Público Brasil nos HTMLs gerados pelo dbt docs e pelo Elementary.

Nenhuma das duas ferramentas aceita tema ou logo próprio, então o HTML pronto recebe o título, o ícone da aba
e um atalho flutuante de volta à página inicial. O logo de cada ferramenta continua na própria interface, para
quem lê saber de onde vem. Cada troca falha alto se o trecho esperado sumir (versão nova da ferramenta).
"""

import re
from urllib.parse import quote

from dado_publico_brasil.core.settings import SITE_DIR

STYLE = (
    "#cpb-voltar{position:fixed;right:16px;bottom:16px;z-index:2147483647;display:flex;align-items:center;"
    "gap:8px;padding:6px 14px 6px 6px;border:1px solid #d9d3c2;border-radius:999px;background:#fffdf8;"
    "color:#0f1f1a;font:600 13px/1.2 Inter,system-ui,sans-serif;text-decoration:none;"
    "box-shadow:0 6px 20px -8px #0f1f1a66}#cpb-voltar svg{width:28px;height:28px}"
    "#cpb-voltar:hover{border-color:#0b5d3b}"
    "#cpb-voltar:focus-visible{outline:3px solid #0b5d3b;outline-offset:2px}"
)


def apply(html: str, title: str) -> str:
    """Troca título e ícone da aba e acrescenta o atalho para a página inicial do lake."""
    symbol = (SITE_DIR / "simbolo.svg").read_text(encoding="utf-8").strip()
    icon = f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,{quote(symbol, safe="")}">'
    decorative = symbol.replace(' role="img"', ' aria-hidden="true"')
    link = (
        f'<style>{STYLE}</style><a id="cpb-voltar" href="/" title="Voltar à página inicial">'
        f"{decorative}<span>Dado Público Brasil</span></a>"
    )
    html, titles = re.subn(r"<title>[^<]*</title>", f"<title>{title}</title>", html, count=1)
    html, icons = re.subn(r'<link[^>]*rel="(?:shortcut )?icon"[^>]*>', lambda _: icon, html, count=1)
    if not (titles and icons and "</body>" in html):
        raise ValueError("HTML sem título, ícone ou </body>: a ferramenta mudou o formato")
    return html.replace("</body>", link + "</body>", 1)
