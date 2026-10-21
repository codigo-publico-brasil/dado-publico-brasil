"""Resolução de identidade de pessoas (ADR 0004): código próprio, não há ferramenta pronta.

Pessoa tem chave própria (sequência, nunca reaproveitada); o identificador de cada fonte fica na
tabela-ponte `identity.pessoa_identificador`, com método, quem confirmou e quando. Regra de ligação
(conservadora): só por identificador oficial da própria fonte; nunca por nome. Os atributos da
pessoa (nome, foto...) não ficam aqui: o dbt os une à chave nos modelos de intermediate e marts.

Lê `intermediate.int_deputados_ids_unidos` (saída da primeira fase do dbt) e cria só as pessoas novas.
"""

from plataforma_dados.core import runs
from plataforma_dados.core.warehouse import Connection, scalar

SOURCE = "camara"
ID_TYPE = "deputado"
METHOD = "identificador oficial da própria fonte"
CONFIRMED_BY = "regra automática"
SEEN = "intermediate.int_deputados_ids_unidos"


def resolve(con: Connection) -> tuple[int, int]:
    """Cria as pessoas que ainda não existem. Devolve (identificadores vistos, pessoas novas)."""
    with runs.track(con, "identity", SOURCE) as run:
        con.execute(
            "CREATE OR REPLACE TEMP TABLE new_people AS "
            "SELECT nextval('identity.seq_pessoa') AS id_pessoa, CAST(s.deputado_id AS VARCHAR) AS source_id "
            f"FROM {SEEN} s WHERE NOT EXISTS ("
            "SELECT 1 FROM identity.pessoa_identificador i "
            "WHERE i.source = ? AND i.id_type = ? AND i.source_id = CAST(s.deputado_id AS VARCHAR))",
            (SOURCE, ID_TYPE),
        )
        moment = runs.now()
        con.execute("INSERT INTO identity.pessoa SELECT id_pessoa, ? FROM new_people", (moment,))
        con.execute(
            "INSERT INTO identity.pessoa_identificador "
            "SELECT ?, ?, source_id, id_pessoa, ?, ?, ? FROM new_people",
            (SOURCE, ID_TYPE, METHOD, CONFIRMED_BY, moment),
        )
        seen = int(scalar(con, f"SELECT COUNT(*) FROM {SEEN}"))
        created = int(scalar(con, "SELECT COUNT(*) FROM new_people"))
        run.rows_in, run.rows_out = seen, created
        return seen, created
