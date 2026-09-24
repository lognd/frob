"""Positive control: SQL102 -- a bare `.all()` call with no `.limit(...)`
in the same chain.

frob:ticket T-5337
"""


def list_all_orders(session):
    """Unbounded fetch on a request path: no `.limit(...)` anywhere.

    frob:ticket T-5337
    """
    return session.query(Order).all()
