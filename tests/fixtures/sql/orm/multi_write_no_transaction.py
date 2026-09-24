"""Positive control: SQL105 -- two write calls in one function with no
wrapping construct around them.

frob:ticket T-5337
"""


def transfer_funds(session, from_account, to_account, amount):
    """Two writes with nothing tying them together into one unit.

    frob:ticket T-5337
    """
    from_account.balance -= amount
    to_account.balance += amount
    from_account.save()
    to_account.save()
