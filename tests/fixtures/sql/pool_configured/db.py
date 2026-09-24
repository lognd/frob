"""Negative control: the same SQL surface as pool_missing/db.py, but
this root also declares pool config (pool_size) -- no SQL106 finding.

frob:ticket T-5337
"""

ENGINE_OPTS = {"pool_size": 10, "max_overflow": 5}


def fetch_user(cursor, user_id):
    """A real SQL-executing call site, so `sql_relevance` is True.

    frob:ticket T-5337
    """
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
