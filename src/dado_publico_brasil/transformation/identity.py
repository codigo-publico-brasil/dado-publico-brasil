"""Resolução de identidade de pessoas (ADR 0004): código próprio, não há ferramenta pronta.

Pessoa tem chave própria (sequência, nunca reaproveitada); o identificador de cada fonte fica na
tabela-ponte `identity.pessoas_identificadores`, com método, quem confirmou e quando. Regra de ligação
(conservadora): só por identificador oficial da própria fonte; nunca por nome. Os atributos da
pessoa (nome, foto...) não ficam aqui: o dbt os une à chave nos modelos de intermediate e marts.

Lê `intermediate.int_pessoas_ids_vistos` (saída da primeira fase do dbt, todas as fontes) e cria só as
pessoas novas. Depois aplica `intermediate.int_vinculos_propostos` (ADR 0013): o registro de uma fonte de
vínculo derivado ganha a pessoa a que se liga, e duas pessoas que a regra mostra serem a mesma (deputado que
virou senador) são fundidas: a chave mais nova é absorvida pela mais antiga e a fusão fica em
`identity.pessoas_fusoes`.

Por fim dá pessoa a todo registro agrupado (ADR 0031): os registros do mesmo grupo
(`intermediate.int_pessoas_grupos`) são uma pessoa só. A âncora é o registro (estável), nunca o grupo. Se o
grupo já toca pessoas, a do cadastro oficial sobrevive; dois cadastros oficiais nunca se fundem por aqui.

Que fontes são cadastro oficial (menor precedência) e quais têm vínculo derivado vem da seed
`intermediate.fontes_identidade` (ADR 0053): o código não nomeia fonte.
"""

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection, scalar

METHOD = "identificador oficial da própria fonte"
CONFIRMED_BY = "regra automática"
SEEN = "intermediate.int_pessoas_ids_vistos"
LINKS = "intermediate.int_vinculos_propostos"
GROUPS = "intermediate.int_pessoas_grupos"
SOURCES = "intermediate.fontes_identidade"
BRIDGE = "identity.pessoas_identificadores"
# cadastro oficial = a menor precedência da seed; vínculo derivado = recalculado a cada execução
OFFICIAL = f"(SELECT fonte FROM {SOURCES} WHERE precedencia = (SELECT min(precedencia) FROM {SOURCES}))"
DERIVED = f"(SELECT fonte FROM {SOURCES} WHERE fl_vinculo_derivado)"


TABLES = ("pessoas", "pessoas_identificadores", "pessoas_fusoes")


def fingerprint(con: Connection) -> str:
    """Impressão digital da identidade: contagem e soma do hash das linhas das três tabelas (segundos).

    Mudou = alguma pessoa, ligação ou fusão mudou, e todo modelo que lê `identity.*` precisa ser refeito."""
    return ";".join(
        f"{t}:{n}:{h}"
        for t in TABLES
        for n, h in [
            con.execute(f"SELECT count(*), coalesce(sum(hash(t)::HUGEINT), 0) FROM identity.{t} t").fetchone()
            or (0, 0)
        ]
    )


def resolve(con: Connection) -> tuple[int, int]:
    """Cria as pessoas que ainda não existem. Devolve (identificadores vistos, pessoas novas)."""
    with runs.track(con, "identity") as run:
        run.impressao_antes = fingerprint(con)
        con.execute(
            "BEGIN"
        )  # tudo ou nada: uma queda no meio de uma fusão não deixa ponte para pessoa apagada
        try:
            created = _resolve(con)
        except BaseException:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
        seen = int(scalar(con, f"SELECT COUNT(*) FROM {SEEN}"))
        run.rows_in, run.rows_out = seen, created
        run.impressao_depois = fingerprint(con)
        return seen, created


def _resolve(con: Connection) -> int:
    """Os passos da resolução; quem chama os envolve numa transação. Devolve as pessoas novas."""
    con.execute(
        "CREATE OR REPLACE TEMP TABLE new_people AS "
        "SELECT nextval('identity.seq_pessoas') AS id_pessoa, s.fonte, s.id_tipo, s.id_na_fonte "
        f"FROM {SEEN} s WHERE NOT EXISTS ("
        "SELECT 1 FROM identity.pessoas_identificadores i "
        "WHERE i.fonte = s.fonte AND i.id_tipo = s.id_tipo AND i.id_na_fonte = s.id_na_fonte)"
    )
    moment = runs.now()
    con.execute("INSERT INTO identity.pessoas SELECT id_pessoa, ? FROM new_people", (moment,))
    con.execute(
        "INSERT INTO identity.pessoas_identificadores "
        "SELECT fonte, id_tipo, id_na_fonte, id_pessoa, ?, ?, ? FROM new_people",
        (METHOD, CONFIRMED_BY, moment),
    )
    _link(con, moment)
    grouped_created = _people_of_groups(con, moment)
    return int(scalar(con, "SELECT COUNT(*) FROM new_people")) + grouped_created


def _same(alias: str, *columns: str) -> str:
    return f"({alias}.fonte, {alias}.id_tipo, {alias}.id_na_fonte) = ({', '.join('v.' + c for c in columns)})"


def _link(con: Connection, moment: str) -> None:
    """Aplica os vínculos propostos: funde as chaves que são a mesma pessoa e liga as candidaturas."""
    origin = _same("a", "origem_fonte", "origem_tipo", "id_origem")
    target = _same("b", "destino_fonte", "destino_tipo", "id_destino")
    con.execute(
        "CREATE OR REPLACE TEMP TABLE fusions AS "
        "SELECT least(a.id_pessoa, b.id_pessoa) AS survivor, greatest(a.id_pessoa, b.id_pessoa) AS absorbed, "
        f"any_value(v.metodo) AS metodo FROM {LINKS} v "
        f"JOIN {BRIDGE} a ON {origin} JOIN {BRIDGE} b ON {target} "
        f"WHERE v.origem_fonte NOT IN {DERIVED} AND a.id_pessoa <> b.id_pessoa GROUP BY 1, 2"
    )
    con.execute(
        "INSERT INTO identity.pessoas_fusoes SELECT absorbed, survivor, metodo, ? FROM fusions", (moment,)
    )
    con.execute(
        f"UPDATE {BRIDGE} SET id_pessoa = f.survivor FROM fusions f WHERE {BRIDGE}.id_pessoa = f.absorbed"
    )
    con.execute("DELETE FROM identity.pessoas WHERE id_pessoa IN (SELECT absorbed FROM fusions)")
    # As ligações das fontes derivadas são recalculadas a cada execução. Uma que deixou de ser proposta (a
    # chave do registro mudou, ou surgiu um homônimo) sai; as aprovadas à mão entram pela mesma tabela. As do
    # grupo (método do modelo de grupos) ficam; sem grupo, nada se apaga (modelo vazio não diz o que fica).
    con.execute(
        f"DELETE FROM {BRIDGE} WHERE fonte IN {DERIVED} AND EXISTS (SELECT 1 FROM {GROUPS}) "
        f"AND metodo NOT IN (SELECT metodo FROM {GROUPS}) AND NOT EXISTS ("
        f"SELECT 1 FROM {LINKS} v WHERE v.origem_fonte = {BRIDGE}.fonte AND v.origem_tipo = {BRIDGE}.id_tipo "
        f"AND v.id_origem = {BRIDGE}.id_na_fonte)"
    )
    con.execute(
        f"INSERT INTO {BRIDGE} "
        "SELECT v.origem_fonte, v.origem_tipo, v.id_origem, b.id_pessoa, v.metodo, ?, ? "
        f"FROM {LINKS} v JOIN {BRIDGE} b ON {target} WHERE v.origem_fonte IN {DERIVED} AND NOT EXISTS "
        f"(SELECT 1 FROM {BRIDGE} a WHERE {origin})",
        (CONFIRMED_BY, moment),
    )


def _group_people_sql() -> str:
    """Pessoas que cada grupo já toca: pela ponte e pelos vínculos propostos. O grupo vale dentro da fonte."""
    target = _same("d", "destino_fonte", "destino_tipo", "id_destino")
    return (
        f"SELECT g.grupo, b.id_pessoa, g.metodo_fusao FROM group_members g JOIN {BRIDGE} b "
        "ON b.fonte = g.fonte AND b.id_na_fonte = g.id_na_fonte "
        f"UNION SELECT g.grupo, d.id_pessoa, g.metodo_fusao FROM group_members g JOIN {LINKS} v "
        f"ON v.origem_fonte = g.fonte AND v.id_origem = g.id_na_fonte JOIN {BRIDGE} d ON {target}"
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


def _people_of_groups(con: Connection, moment: str) -> int:
    """Dá pessoa a todo registro agrupado e funde as que um grupo mostra serem uma só. Devolve as novas."""
    con.execute(
        "CREATE OR REPLACE TEMP TABLE group_members AS "
        "SELECT fonte, id_tipo, id_na_fonte, metodo, metodo_fusao, fonte || ':' || grupo AS grupo "
        f"FROM {GROUPS}"
    )
    official = {
        int(r[0])
        for r in con.execute(f"SELECT DISTINCT id_pessoa FROM {BRIDGE} WHERE fonte IN {OFFICIAL}").fetchall()
    }
    rows = con.execute(_group_people_sql()).fetchall()
    fusion_of = {int(p): m for _, p, m in sorted(rows, key=lambda r: (r[0], r[1]))}
    for component in _components([(g, int(p)) for g, p, _ in rows]):
        # dois cadastros oficiais nunca se fundem por um grupo: o grupo fica como está (teste de lacuna)
        officials = component & official
        if len(officials) > 1:
            continue
        survivor = next(iter(officials)) if officials else min(component)
        for absorbed in sorted(component - {survivor}):
            con.execute(
                "INSERT INTO identity.pessoas_fusoes VALUES (?, ?, ?, ?)",
                (absorbed, survivor, fusion_of[absorbed], moment),
            )
            con.execute(f"UPDATE {BRIDGE} SET id_pessoa = ? WHERE id_pessoa = ?", (survivor, absorbed))
            con.execute("DELETE FROM identity.pessoas WHERE id_pessoa = ?", (absorbed,))
    # grupos que ainda não têm pessoa ganham uma; depois todo registro do grupo entra na ponte
    con.execute(
        "CREATE OR REPLACE TEMP TABLE group_people AS "
        f"SELECT DISTINCT grupo, id_pessoa FROM ({_group_people_sql()})"
    )
    con.execute(
        "CREATE OR REPLACE TEMP TABLE new_group_people AS "
        "SELECT grupo, nextval('identity.seq_pessoas') AS id_pessoa FROM "
        "(SELECT DISTINCT grupo FROM group_members "
        "WHERE grupo NOT IN (SELECT grupo FROM group_people) ORDER BY grupo)"
    )
    con.execute("INSERT INTO identity.pessoas SELECT id_pessoa, ? FROM new_group_people", (moment,))
    con.execute("INSERT INTO group_people SELECT grupo, id_pessoa FROM new_group_people")
    # só entra na ponte o grupo com uma pessoa só; o que ainda toca mais de uma fica de fora (teste de lacuna)
    con.execute(
        f"INSERT INTO {BRIDGE} SELECT g.fonte, g.id_tipo, g.id_na_fonte, p.id_pessoa, g.metodo, ?, ? "
        "FROM group_members g JOIN (SELECT grupo, min(id_pessoa) AS id_pessoa FROM group_people "
        "GROUP BY grupo HAVING count(*) = 1) p USING (grupo) "
        f"WHERE NOT EXISTS (SELECT 1 FROM {BRIDGE} b WHERE b.fonte = g.fonte AND b.id_tipo = g.id_tipo "
        "AND b.id_na_fonte = g.id_na_fonte)",
        (CONFIRMED_BY, moment),
    )
    return int(scalar(con, "SELECT COUNT(*) FROM new_group_people"))
