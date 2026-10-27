"""Municípios sintéticos no formato real da API de localidades do IBGE; sem rede."""

import json
from pathlib import Path

from dado_publico_brasil.ingestion import contract as contracts


def _municipio(
    codigo: int, nome: str, uf: str, uf_nome: str, regiao: str, regiao_nome: str
) -> dict[str, object]:
    return {
        "id": codigo,
        "nome": nome,
        "microrregiao": None,
        "regiao-imediata": {
            "id": 330001,
            "nome": "Imediata",
            "regiao-intermediaria": {
                "id": 3301,
                "nome": "Intermediária",
                "UF": {
                    "id": 33,
                    "sigla": uf,
                    "nome": uf_nome,
                    "regiao": {"id": 3, "sigla": regiao, "nome": regiao_nome},
                },
            },
        },
    }


def ibge_files(pasta: Path) -> dict[str, Path]:
    """O arquivo sintético do IBGE, pela URL oficial. O 60011 do TSE (RJ) bate por nome e UF; o outro não existe lá."""
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "municipios.json"
    municipios = [
        _municipio(3300001, "Município 60011", "RJ", "Rio de Janeiro", "SE", "Sudeste"),
        _municipio(3500002, "São Paulo", "SP", "São Paulo", "SE", "Sudeste"),
        _municipio(3500003, "São Paulo", "RJ", "Rio de Janeiro", "SE", "Sudeste"),  # mesmo nome em outra UF
    ]
    arquivo.write_text(json.dumps(municipios, ensure_ascii=False), encoding="utf-8")
    return {contracts.find("ibge").url("municipios", None): arquivo}
