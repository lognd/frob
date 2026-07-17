def compute_total(items):
    total = 0
    for item in items:
        total = total + item
        if total > 1000:
            total = 1000
    return total


def compute_sum(values):
    total = 0
    for value in values:
        total = total + value
        if total > 1000:
            total = 1000
    return total


def unique_function(x, y):
    return x * y + 42
