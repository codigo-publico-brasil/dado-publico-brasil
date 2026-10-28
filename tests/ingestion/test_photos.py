"""Nome dos arquivos de foto dos pacotes do TSE: com F até 2018 em diante, sem F de 2006 a 2014."""

import pytest

from dado_publico_brasil.ingestion import photos


@pytest.mark.parametrize(
    ("name", "sq", "extension"),
    [
        ("FRJ190001623300_div.jpg", "190001623300", "jpg"),
        ("FBR280001234567_div.jpeg", "280001234567", "jpeg"),
        ("BR280000000001_div.jpg", "280000000001", "jpg"),  # layout de 2006 a 2014
        ("SP250000000123_div.jpg", "250000000123", "jpg"),
    ],
)
def test_both_layouts_of_the_photo_package_give_the_candidate_sequence(
    name: str, sq: str, extension: str
) -> None:
    found = photos.MEMBER.match(name)
    assert found is not None
    assert (found.group(1), found.group(2)) == (sq, extension)


@pytest.mark.parametrize("name", ["Thumbs.db", "FRJ1001_div.png", "RJ1001.jpg", "FRJ1001_miniatura.jpg"])
def test_other_files_in_the_package_are_ignored(name: str) -> None:
    assert photos.MEMBER.match(name) is None
