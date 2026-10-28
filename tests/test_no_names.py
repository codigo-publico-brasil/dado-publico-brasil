"""Nenhum nome de candidato, partido ou informação do tipo em documentação, código e testes.

Exemplos usam rótulos genéricos ("Pessoa Exemplo", "Partido A"). A exceção são as tabelas de referência em
`dbt/seeds/` (dado com fonte oficial). A lista de nomes e siglas conhecidos fica só como hash (SHA-256), para o
próprio teste não conter nenhum. Siglas ambíguas (PL e PT, por exemplo, também são projeto de lei e outras
coisas) ficam de fora: a trava cobre o que é inequívoco e não é uma varredura completa.

Para acrescentar um nome ou sigla à lista, calcule o hash do token (siglas como escritas, nomes em minúsculas):
`python -c "import hashlib; print(hashlib.sha256('TOKEN'.encode()).hexdigest())"` e inclua o resultado no conjunto.
"""

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PREFIXES = ("dbt/seeds/", "dbt/dbt_packages/", ".venv/")
SKIP_SUFFIXES = (".lock", ".png", ".jpg", ".zip", ".duckdb")
TOKEN = re.compile(r"[\wÀ-ÿ]+")

# SHA-256 de siglas de partidos (como escritas, em maiúsculas) e de nomes (em minúsculas)
PARTIES = set(
    [
        "06b71eaca9c6620be89d6c291135421ff84f73fb6e06bacdac923a283ad1b123",
        "1395a46d5673fedf702ede340f7f4560f3e0785480a2d25cf0bf132475011eb8",
        "19a74e4b854089409b2da8ce43f433de09b805909337fe43010379d37b120a82",
        "3e7e7df2c050b6e01c7ae5a55f17eb8a6e83ab8567503d00f748c0031c169129",
        "41f192f977e250ac6c9a53947c56b36974771917f83c052e833e1ac387cdd6f7",
        "489334d05947807e2d3d851fcd15bf8c8332285c889797a41a83ec9fd7753231",
        "53cab12c5d975eb82f01530be34060cad30f8f02604b65d81786c0d80e5a8398",
        "61f9580ba75d65d606ba53ceabc4b77fda1fdc1eb209f7db5a8a9d2f65a4db22",
        "6558038e726e98cc4604570a467525f203ad5f5a2e9eba6e1b769fa55f46fa70",
        "7b9ab6896b4c377e63103bd4323d2a18386cc63043a709b0f7185d0f55d06b1b",
        "7e9bc4211017683f7f41ed94eafe7fc645173663d8fe2742702ed735d86d6e57",
        "800bf1e2802c9dd26560013bb8657c91298df848b0ecb424d8e5f61ca5dfe27e",
        "81bcf02c22eb259433e1458c3b734311794bb5f96b4acd773783a24862236715",
        "880505c2d3ddea8f5655aae6e75a8641cb56f491232d5b3d1d69d6b6240b8c89",
        "8922d7621e8d97069802209e5e2905412f53e0006fb530bde2a0678bec9930b4",
        "a429a7da1255c729fabd55661ead7a08bc13169d56e247d0e4cd3ebc8b76c3ab",
        "b3aaceeedbc84b76c1935051c50b18146a4824eb29efb215015fd1f5b7ccaca3",
        "b5a9ef88bd8c6a82281f98b2390ab05802d460272d8c7d98d954cdb238868226",
        "c217ce766d6930f4c82c721bd81473a61f5fec023d6bcf03baf49cad774e4ced",
        "c78c59fb6abf1b5994d2f9e6f5074c57f62b4aad48990d434bf3161a526edc16",
        "c9f53bc11399bad58627afaead7b81400cc49b1b63e13ce4bc06120947c800c8",
        "d37ef011dd0498513aa0aa91a9b59388417f481760a4789dd2d1bd150620dd6c",
        "df3041cf9a7e98ba49a1c89d94fb39d6215f1559e088de5cc90dab2bb4ac6592",
        "e35380c346b68e15db6999388163811e3fe5535b52bb0b7f4ee6ef9cfaeb404a",
        "e3a9669f46fbd4ea0ed648e28ac680f38db35115587edf72bd0252056ccae13c",
        "e56a7d91a8497ef2540e67b20fddeb9b894669b4cb52dad210db128e6a2d604b",
        "f29cfc8698e1fb438d2bd05650947d1544ad7c231d0f455e0007cd24aacbb575",
    ]
)
NAMES = set(
    [
        "0f9dbab494594994c643ed8220cec23a90eb30fb75cc02001d1079748e6fd542",
        "101a60c1c876a86ad54d821fe97b30d1278fceaaeafe7f70040fcc689fb0b433",
        "192019e1cacba022f77af9c201dc03c21dc3155587a19cc4f85c57ac7fdfb326",
        "1cc0f153d6cd370efa1900fdb3aa0c2c060edf0fa5b1db6750838c07e6853067",
        "2cd79c5c73bcd9e0ccfdfceda36b46fc453cbfccd9063baab4d37ca18896c399",
        "3c40c2ab826e281f34814ef7d91cb3924402cce258565c5172aadc04b189b8b0",
        "3e90907fc3ad3c1ade8d3a925494960f060628506baf16795575c29c15993aeb",
        "489eb0e8fa3e977ad1420f1c75de55025d434d460c6692188b69994702baf3c1",
        "5f77c2500f56fe1a4abe06bf961012a3ea513ce8fbbbf4fec4d58339f95630d9",
        "6c7269bc99bb0806d6ab44d83e05d71b57fcd60bbbd4b9825acac92438369e09",
        "7a58b77f141b05b90fc5ecac63d405ebb9559f1dc8537acbafcbd0e0581c38eb",
        "7f8f05e613fcd0cad242bdd5754f5c927ab0332090dff4ba7a1af3e1630d1074",
        "84381eb69a68ef1bc723b3403cfd775c8f8026df17b9dfb414307fa9c13b511e",
        "8a6d677f9cbb3164ef336a2148f47f772f567ba63a5a68ff3596e61a447b36a4",
        "8b0cee02fa28dfcd7c6bebd022ac4fc0e6b5995da0fd82ac7037b7d3b3711d8e",
        "8bd4cc410ac20e39c05e480a5b76714d7f0903bb22c831433ed997776541845b",
        "8e3f5e915594cdb4ef687b3c65e4706ffa0abefadc91934f0add9ce4570e4700",
        "99cb2f9b05f6f0c2056bb18cf8230f6f01aabddeb4e102a4de5717e437658da4",
        "a2f257bd34b48cf32c56e82fb753acd316a097ffdaff7bd4956e4e82fa7ceffc",
        "aa634f52aee3e30aec9a43e42db52c212f3ce136d197079930bbc7a324f56d3e",
        "bb9bbad80b8b34e85654aafb9214155a67df3beeac034d8955df629d428e5ec6",
        "c1211b771f152c939a84dd83bf2487b38b98ae947f5216f778a4a496c64eb756",
        "c84baefaf76f5d9aee40577d590470d1c28b217bee2ecd103c86b4602b4c05ef",
        "cfa08c7fa5b1d464f86e70566423d2b7987842796963414886615ad0c8a4eaeb",
        "da911ec9c2c5ea51263f406e00a6996711ce0c891095dceac46fc9a8e4bf1532",
        "dae2103aba4abe56095cc4dcf9a000df0d0ed7a664aa187ebed5a9eb9224fea9",
        "ed4490866480be6441ba15e6151fddd530b60eedf5736d0aba7f6ac69f07c51a",
        "f83c31f2a4558a2223e1f58d52cd7b3c8e6cf42da50dfc455f61b02b454f7bb0",
        "f85c16577d8a6f9ea75feb853c97ad1245c8e96dad30937dcf04c5e832ccec0d",
        "ff564d7184e4bcb7f387cda1ae6fde10868a94ed4a524ef5edac4aaee9454571",
    ]
)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tracked_text_files() -> list[Path]:
    names = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [
        ROOT / n
        for n in names
        if not n.startswith(SKIP_PREFIXES) and not n.endswith(SKIP_SUFFIXES) and (ROOT / n).is_file()
    ]


def forbidden_lines(text: str) -> list[int]:
    """Números das linhas (de 1) que citam um nome ou uma sigla da lista. Usado também pelo gancho dos agentes."""
    return [
        number
        for number, line in enumerate(text.splitlines(), 1)
        if any(digest(t) in PARTIES or digest(t.lower()) in NAMES for t in TOKEN.findall(line))
    ]


def test_docs_code_and_tests_cite_no_candidate_or_party_names() -> None:
    found: list[str] = []
    for path in tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found += [f"{path.relative_to(ROOT).as_posix()}:{n}" for n in forbidden_lines(text)]
    assert found == [], (
        "nome ou sigla de partido em exemplo, texto ou código; use rótulo genérico: " + ", ".join(found)
    )
