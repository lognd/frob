"""Negative control: the same two-write shape as
multi_write_no_transaction.py, but inside an `atomic()` block -- no
SQL105 finding.

frob:ticket T-5337
"""


def transfer_funds(session, from_account, to_account, amount):
    """Two writes wrapped in `atomic()`: no SQL105 finding.

    frob:ticket T-5337
    """
    with atomic():
        from_account.balance -= amount
        to_account.balance += amount
        from_account.save()
        to_account.save()
