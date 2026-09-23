"""Negative control: psycopg's sql.SQL/sql.Identifier composition API --
excluded from WEBSEC107 (a safe, parameterized composition primitive per
the T-5141 corpus, not a taint sink).

frob:ticket T-5334
"""

from psycopg import sql


def fetch_dynamic_table(cursor, table_name):
    """Compose a query against a dynamic table name through psycopg's
    safe sql.SQL/sql.Identifier API -- no WEBSEC107 finding expected.

    frob:ticket T-5334
    """
    cursor.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name)))
    return cursor.fetchall()
