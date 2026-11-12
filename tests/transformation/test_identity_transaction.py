"""A resolução de pessoas é tudo ou nada: uma queda no meio de uma fusão não muda a identidade."""

from pathlib import Path

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import scalar
from dado_publico_brasil.transformation import identity


def test_a_failure_in_the_middle_of_a_fusion_leaves_the_identity_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    con = migrations.open_warehouse(Settings(storage_root=tmp_path))
    con.execute("CREATE SCHEMA intermediate")
    con.execute(
        "CREATE TABLE intermediate.int_pessoas_ids_vistos (fonte VARCHAR, id_tipo VARCHAR, id_na_fonte VARCHAR)"
    )
    con.execute(
        "INSERT INTO intermediate.int_pessoas_ids_vistos VALUES ('camara', 'deputado', '1'), ('senado', 'senador', '2')"
    )
    con.execute(
        "CREATE TABLE intermediate.int_vinculos_propostos (origem_fonte VARCHAR, origem_tipo VARCHAR, "
        "id_origem VARCHAR, destino_fonte VARCHAR, destino_tipo VARCHAR, id_destino VARCHAR, metodo VARCHAR)"
    )
    con.execute(
        "CREATE TABLE intermediate.int_pessoas_grupos (fonte VARCHAR, id_tipo VARCHAR, id_na_fonte VARCHAR, "
        "grupo VARCHAR, metodo VARCHAR, metodo_fusao VARCHAR)"
    )
    con.execute(
        "CREATE TABLE intermediate.fontes_identidade (fonte VARCHAR, precedencia INTEGER, fl_vinculo_derivado BOOLEAN)"
    )
    con.execute(
        "INSERT INTO intermediate.fontes_identidade VALUES ('camara', 1, false), ('senado', 1, false), ('tse', 2, true)"
    )
    assert identity.resolve(con) == (2, 2)  # duas pessoas, ainda sem vínculo
    con.execute(
        "INSERT INTO intermediate.int_vinculos_propostos VALUES "
        "('senado', 'senador', '2', 'camara', 'deputado', '1', 'regra')"
    )
    before = identity.fingerprint(con)

    def fail(*_: object) -> int:
        raise RuntimeError("queda no meio da fusão")

    monkeypatch.setattr(
        identity, "_people_of_groups", fail
    )  # roda depois de a fusão apagar a pessoa absorvida
    with pytest.raises(RuntimeError, match="queda"):
        identity.resolve(con)
    assert identity.fingerprint(con) == before
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas") == 2
    assert scalar(con, "SELECT resultado FROM metadata.execucoes ORDER BY id_execucao DESC") == "error"

    monkeypatch.undo()
    identity.resolve(con)  # sem a falha, a mesma fusão se completa
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas") == 1
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas_fusoes") == 1
