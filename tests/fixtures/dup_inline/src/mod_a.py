def process_orders(items):
    return _finalize_a(items)


def process_receipts(values):
    return _finalize_b(values)


def _finalize_a(items):
    total = 0
    for item in items:
        total = total + item
    if total > 1000:
        total = 1000
    return total


def _finalize_b(values):
    total = 0
    for value in values:
        total = total + value
    if total > 1000:
        total = 1000
    return total


def unrelated_thing(x, y):
    return x * y + 42
