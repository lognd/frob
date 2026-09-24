"""Positive control: SQL101 -- a lazy relationship touched per row
inside a loop, no eager fetch anywhere in the function.

frob:ticket T-5337
"""


def list_customer_names(session):
    """Classic N-plus-one: `order.customer` is fetched lazily on every
    loop iteration.

    frob:ticket T-5337
    """
    orders = session.query(Order).all()
    names = []
    for order in orders:
        names.append(order.customer.name)
    return names
