"""Pessoas Expostas Politicamente (`sources/executivo/federal/pep.yml`).

O portal só mantém o arquivo do último mês publicado: os anteriores respondem 403 (o armazenamento esconde o
que não existe). `download` é o padrão, mas esse 403 vira falha comum de rede (`availability`) e
não bloqueio, que interromperia a fonte; 405 e 429 continuam sendo bloqueio.
"""

from pathlib import Path

from dado_publico_brasil.ingestion import fetch


def download(url: str, folder: Path) -> tuple[Path, str, int]:
    try:
        return fetch.download(url, folder, suffix="zip", sites=("cgu.gov.br",))
    except fetch.SourceBlocked as error:
        if error.status == 403:
            raise OSError(f"{url}: arquivo não publicado ou já retirado pela fonte") from error
        raise
