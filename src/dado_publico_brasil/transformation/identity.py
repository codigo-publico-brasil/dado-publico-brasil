"""Resolução de identidade de pessoas (ADR 0004): código próprio, não há ferramenta pronta.

Pessoa tem chave própria (sequência, nunca reaproveitada); o identificador de cada fonte fica na
tabela-ponte `identity.pessoa_identificador`, com método, quem confirmou e quando. Regra de ligação
(conservadora): só por identificador oficial da própria fonte; nunca por nome. Os atributos da
pessoa (nome, foto...) não ficam aqui: o dbt os une à chave nos modelos de intermediate e marts.

Lê `intermediate.int_pessoas_ids_vistos` (saída da primeira fase do dbt, todas as fontes) e cria só as
pessoas novas. Depois aplica `intermediate.int_vinculos_propostos` (ADR 0013): a candidatura do TSE ganha a
pessoa a que se liga, e duas pessoas que a regra mostra serem a mesma (deputado que virou senador) são
fundidas: a chave mais nova é absorvida pela mais antiga e a fusão fica em `identity.pessoa_fusao`.

Por fim dá pessoa a todo eleito do TSE (ADR 0031): as candidaturas do mesmo grupo (`int_tse_eleitos_grupos`)
são uma pessoa só. A âncora é `id_candidatura` (estável), nunca o grupo. Se o grupo já toca pessoas, a
pessoa oficial (Câmara ou Senado) sobrevive; duas oficiais nunca se fundem por aqui.
"""

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection, scalar

METHOD = "identificador oficial da própria fonte"
CONFIRMED_BY = "regra automática"
SEEN = "intermediate.int_pessoas_ids_vistos"
LINKS = "intermediate.int_vinculos_propostos"
GROUPS = "intermediate.int_tse_eleitos_grupos"
BRIDGE = "identity.pessoa_identificador"
ELECTED_TYPE = "candidatura_de_eleito"
GROUP_METHOD = "candidaturas do mesmo grupo de eleito no TSE"
GROUP_FUSION = "mesmo grupo de candidaturas do TSE"


def resolve(con: Connection) -> tuple[int, int]:
    """Cria as pessoas que ainda não existem. Devolve (identificadores vistos, pessoas novas)."""
    with runs.track(con, "identity") as run:
        con.execute(
            "CREATE OR REPLACE TEMP TABLE new_people AS "
            "SELECT nextval('identity.seq_pessoa') AS id_pessoa, s.fonte, s.id_tipo, s.id_na_fonte "
            f"FROM {SEEN} s WHERE NOT EXISTS ("
            "SELECT 1 FROM identity.pessoa_identificador i "
            "WHERE i.source = s.fonte AND i.id_type = s.id_tipo AND i.source_id = s.id_na_fonte)"
        )
        moment = runs.now()
        con.execute("INSERT INTO identity.pessoa SELECT id_pessoa, ? FROM new_people", (moment,))
        con.execute(
            "INSERT INTO identity.pessoa_identificador "
            "SELECT fonte, id_tipo, id_na_fonte, id_pessoa, ?, ?, ? FROM new_people",
            (METHOD, CONFIRMED_BY, moment),
        )
        _link(con, moment)
        tse_created = _tse_people(con, moment)
        seen = int(scalar(con, f"SELECT COUNT(*) FROM {SEEN}"))
        created = int(scalar(con, "SELECT COUNT(*) FROM new_people")) + tse_created
        run.rows_in, run.rows_out = seen, created
        return seen, created


def _same(alias: str, *columns: str) -> str:
    return f"({alias}.source, {alias}.id_type, {alias}.source_id) = ({', '.join('v.' + c for c in columns)})"


def _link(con: Connection, moment: str) -> None:
    """Aplica os vínculos propostos: funde as chaves que são a mesma pessoa e liga as candidaturas."""
    origin = _same("a", "origem_fonte", "origem_tipo", "id_origem")
    target = _same("b", "destino_fonte", "destino_tipo", "id_destino")
    con.execute(
        "CREATE OR REPLACE TEMP TABLE fusions AS "
        "SELECT least(a.id_pessoa, b.id_pessoa) AS survivor, greatest(a.id_pessoa, b.id_pessoa) AS absorbed, "
        f"any_value(v.metodo) AS metodo FROM {LINKS} v "
        f"JOIN {BRIDGE} a ON {origin} JOIN {BRIDGE} b ON {target} "
        "WHERE v.origem_fonte <> 'tse' AND a.id_pessoa <> b.id_pessoa GROUP BY 1, 2"
    )
    con.execute(
        "INSERT INTO identity.pessoa_fusao SELECT absorbed, survivor, metodo, ? FROM fusions", (moment,)
    )
    con.execute(
        f"UPDATE {BRIDGE} SET id_pessoa = f.survivor FROM fusions f WHERE {BRIDGE}.id_pessoa = f.absorbed"
    )
    con.execute("DELETE FROM identity.pessoa WHERE id_pessoa IN (SELECT absorbed FROM fusions)")
    # As ligações do TSE são derivadas: a regra as recalcula a cada execução. Uma que deixou de ser proposta
    # (a chave da candidatura mudou, ou surgiu um homônimo) sai; as aprovadas à mão entram pela mesma tabela.
    con.execute(
        f"DELETE FROM {BRIDGE} WHERE source = 'tse' AND method <> '{GROUP_METHOD}' AND NOT EXISTS ("
        f"SELECT 1 FROM {LINKS} v WHERE v.origem_fonte = 'tse' AND v.origem_tipo = {BRIDGE}.id_type "
        f"AND v.id_origem = {BRIDGE}.source_id)"
    )
    con.execute(
        f"INSERT INTO {BRIDGE} "
        "SELECT v.origem_fonte, v.origem_tipo, v.id_origem, b.id_pessoa, v.metodo, ?, ? "
        f"FROM {LINKS} v JOIN {BRIDGE} b ON {target} WHERE v.origem_fonte = 'tse' AND NOT EXISTS "
        f"(SELECT 1 FROM {BRIDGE} a WHERE {origin})",
        (CONFIRMED_BY, moment),
    )


def _group_people_sql() -> str:
    """Pessoas que cada grupo de eleito já toca: pela ponte e pelos vínculos propostos."""
    target = _same("d", "destino_fonte", "destino_tipo", "id_destino")
    return (
        f"SELECT g.grupo, b.id_pessoa FROM {GROUPS} g JOIN {BRIDGE} b "
        "ON b.source = 'tse' AND b.source_id = g.id_candidatura "
        f"UNION SELECT g.grupo, d.id_pessoa FROM {GROUPS} g JOIN {LINKS} v "
        f"ON v.origem_fonte = 'tse' AND v.id_origem = g.id_candidatura JOIN {BRIDGE} d ON {target}"
    )


def _components(pairs: list[tuple[str, int]]) -> list[set[int]]:
    """Une as pessoas que partilham algum grupo; cada conjunto com mais de uma é uma pessoa a fundir."""
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[str, int] = {}
    for group, person in pairs:
        if group in first:
            parent[find(person)] = find(first[group])
        else:
            first[group] = person
            find(person)
    components: dict[int, set[int]] = {}
    for person in parent:
        components.setdefault(find(person), set()).add(person)
    return [c for c in components.values() if len(c) > 1]


def _tse_people(con: Connection, moment: str) -> int:
    """Dá pessoa a todo eleito do TSE e funde as que um grupo mostra serem uma só. Devolve as novas."""
    official = {
        int(r[0])
        for r in con.execute(
            f"SELECT DISTINCT id_pessoa FROM {BRIDGE} WHERE source IN ('camara', 'senado')"
        ).fetchall()
    }
    for component in _components(con.execute(_group_people_sql()).fetchall()):
        # duas oficiais nunca se fundem por um grupo do TSE: o grupo fica como está (teste de lacuna)
        officials = component & official
        if len(officials) > 1:
            continue
        survivor = next(iter(officials)) if officials else min(component)
        for absorbed in sorted(component - {survivor}):
            con.execute(
                "INSERT INTO identity.pessoa_fusao VALUES (?, ?, ?, ?)",
                (absorbed, survivor, GROUP_FUSION, moment),
            )
            con.execute(f"UPDATE {BRIDGE} SET id_pessoa = ? WHERE id_pessoa = ?", (survivor, absorbed))
            con.execute("DELETE FROM identity.pessoa WHERE id_pessoa = ?", (absorbed,))
    # grupos que ainda não têm pessoa ganham uma; depois toda candidatura do grupo entra na ponte
    con.execute(f"CREATE OR REPLACE TEMP TABLE group_people AS {_group_people_sql()}")
    con.execute(
        "CREATE OR REPLACE TEMP TABLE new_tse_people AS "
        "SELECT grupo, nextval('identity.seq_pessoa') AS id_pessoa FROM "
        f"(SELECT DISTINCT grupo FROM {GROUPS} WHERE grupo NOT IN (SELECT grupo FROM group_people))"
    )
    con.execute("INSERT INTO identity.pessoa SELECT id_pessoa, ? FROM new_tse_people", (moment,))
    con.execute("INSERT INTO group_people SELECT grupo, id_pessoa FROM new_tse_people")
    # só entra na ponte o grupo com uma pessoa só; o que ainda toca mais de uma fica de fora (teste de lacuna)
    con.execute(
        f"INSERT INTO {BRIDGE} SELECT 'tse', '{ELECTED_TYPE}', g.id_candidatura, p.id_pessoa, ?, ?, ? "
        f"FROM {GROUPS} g JOIN (SELECT grupo, min(id_pessoa) AS id_pessoa FROM group_people GROUP BY grupo "
        "HAVING count(*) = 1) p USING (grupo) "
        f"WHERE NOT EXISTS (SELECT 1 FROM {BRIDGE} b WHERE b.source = 'tse' AND b.id_type = '{ELECTED_TYPE}' "
        "AND b.source_id = g.id_candidatura)",
        (GROUP_METHOD, CONFIRMED_BY, moment),
    )
    return int(scalar(con, "SELECT COUNT(*) FROM new_tse_people"))
