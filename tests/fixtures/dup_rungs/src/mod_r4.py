def process_gapped_a(items):
    total = 0
    for item in items:
        total = total + item
    return total


def process_gapped_b(items):
    total = 0
    for item in items:
        total = total + item
        if total > 999999:
            total = 999999
    return total


def process_distinct(items):
    return sum(items) * 2
