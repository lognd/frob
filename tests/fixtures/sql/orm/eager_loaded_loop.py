"""Negative control: the same loop shape as n_plus_one_loop.py, but
eager-loaded -- no SQL101 finding.

frob:ticket T-5337
"""


def list_customer_names(session):
    """Eager-loaded via joinedload: no N+1, no SQL101 finding.

    frob:ticket T-5337
    """
    orders = session.query(Order).options(joinedload(Order.customer)).limit(100).all()
    names = []
    for order in orders:
        names.append(order.customer.name)
    return names
