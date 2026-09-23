"""Negative control: DB-API cursor.execute() with an f-string-composed
SQL argument -- WEBSEC107 (CWE-89 SQL injection sink).

frob:ticket T-5334
"""


def fetch_user_unsafe(cursor, table_name):
    """Fetch all rows from `table_name`, injecting the table name directly
    into the SQL string via an f-string -- the exact CWE-89 shape
    WEBSEC107 flags.

    frob:ticket T-5334
    """
    cursor.execute(f"SELECT * FROM {table_name}")
    return cursor.fetchall()
