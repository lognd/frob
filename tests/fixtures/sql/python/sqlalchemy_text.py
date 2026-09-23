"""Positive control: SQLAlchemy's bare text() construct with a literal
SQL string.

frob:ticket T-5334
"""

from sqlalchemy import text


def count_users(connection):
    """Run a literal SQL count query via SQLAlchemy's text() construct.

    frob:ticket T-5334
    """
    return connection.execute(text("SELECT count(*) FROM users")).scalar()
