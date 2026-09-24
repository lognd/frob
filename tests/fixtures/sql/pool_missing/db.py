"""Positive control: SQL106 -- real SQL surface, no pool config token
anywhere under this root.

frob:ticket T-5337
"""


def fetch_user(cursor, user_id):
    """A real SQL-executing call site, so `sql_relevance` is True.

    frob:ticket T-5337
    """
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
