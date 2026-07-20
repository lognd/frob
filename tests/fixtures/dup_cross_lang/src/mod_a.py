def compute_total(items):
    total = 0
    for item in items:
        total = total + item
        if total > 1000:
            total = 1000
    return total
