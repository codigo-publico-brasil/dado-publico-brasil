"""Resolução de identidade de pessoas (ADR 0004): código próprio, não há ferramenta pronta.

Pessoa tem chave própria (sequência, nunca reaproveitada); o identificador de cada fonte fica na
tabela-ponte `identity.pessoa_identificador`, com método, quem confirmou e quando. Regra de ligação
(conservadora): só por identificador oficial da própria fonte; nunca por nome. Os atributos da
pessoa (nome, foto...) não ficam aqui: o dbt os une à chave nos modelos de intermediate e marts.

Lê `intermediate.int_pessoas_ids_vistos` (saída da primeira fase do dbt, todas as fontes) e cria só as
pessoas novas. Depois aplica `intermediate.int_vinculos_propostos` (ADR 0013): a candidatura do TSE ganha a
pessoa a que se liga, e duas pessoas que a regra mostra serem a mesma (deputado que virou senador) são
fundidas: a chave mais nova é absorvida pela mais antiga e a fusão fica em `identity.pessoa_fusao`.
"""

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection, scalar

METHOD = "identificador oficial da própria fonte"
CONFIRMED_BY = "regra automática"
SEEN = "intermediate.int_pessoas_ids_vistos"
LINKS = "intermediate.int_vinculos_propostos"
BRIDGE = "identity.pessoa_identificador"


def resolve(con: Connection) -> tuple[int, int]:
    """Cria as pessoas que ainda não existem. Devolve (identificadores vistos, pessoas novas)."""
    with runs.track(con, "identity") as run:
        con.execute(
            "CREATE OR REPLACE TEMP TABLE new_people AS "
            "SELECT nextval('identity.seq_pessoa') AS id_pessoa, s.fonte, s.tipo_id, s.id_na_fonte "
            f"FROM {SEEN} s WHERE NOT EXISTS ("
            "SELECT 1 FROM identity.pessoa_identificador i "
            "WHERE i.source = s.fonte AND i.id_type = s.tipo_id AND i.source_id = s.id_na_fonte)"
        )
        moment = runs.now()
        con.execute("INSERT INTO identity.pessoa SELECT id_pessoa, ? FROM new_people", (moment,))
        con.execute(
            "INSERT INTO identity.pessoa_identificador "
            "SELECT fonte, tipo_id, id_na_fonte, id_pessoa, ?, ?, ? FROM new_people",
            (METHOD, CONFIRMED_BY, moment),
        )
        _link(con, moment)
        seen = int(scalar(con, f"SELECT COUNT(*) FROM {SEEN}"))
        created = int(scalar(con, "SELECT COUNT(*) FROM new_people"))
        run.rows_in, run.rows_out = seen, created
        return seen, created


def _same(alias: str, *columns: str) -> str:
    return f"({alias}.source, {alias}.id_type, {alias}.source_id) = ({', '.join('v.' + c for c in columns)})"


def _link(con: Connection, moment: str) -> None:
    """Aplica os vínculos propostos: funde as chaves que são a mesma pessoa e liga as candidaturas."""
    origin = _same("a", "origem_fonte", "origem_tipo", "origem_id")
    target = _same("b", "destino_fonte", "destino_tipo", "destino_id")
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
        f"DELETE FROM {BRIDGE} WHERE source = 'tse' AND NOT EXISTS ("
        f"SELECT 1 FROM {LINKS} v WHERE v.origem_fonte = 'tse' AND v.origem_tipo = {BRIDGE}.id_type "
        f"AND v.origem_id = {BRIDGE}.source_id)"
    )
    con.execute(
        f"INSERT INTO {BRIDGE} "
        "SELECT v.origem_fonte, v.origem_tipo, v.origem_id, b.id_pessoa, v.metodo, ?, ? "
        f"FROM {LINKS} v JOIN {BRIDGE} b ON {target} WHERE v.origem_fonte = 'tse' AND NOT EXISTS "
        f"(SELECT 1 FROM {BRIDGE} a WHERE {origin})",
        (CONFIRMED_BY, moment),
    )
