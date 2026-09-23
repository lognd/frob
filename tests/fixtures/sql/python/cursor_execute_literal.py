"""Positive control: DB-API cursor.execute() with a literal SQL string
(no interpolation) -- extracted verbatim, no WEBSEC107 finding.

frob:ticket T-5334
"""


def fetch_user(cursor, user_id):
    """Fetch a user row by id using a parameterized, literal SQL string.

    frob:ticket T-5334
    """
    cursor.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
