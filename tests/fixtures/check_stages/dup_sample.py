"""Fixture for T-4692's golden dup test: two near-identical function bodies
(Type 2 clone -- renamed identifiers, same structure) `frob dup`/`frob
check --only dup` are BOTH required to report. >=20 lines each (T-2970's
`tests/` floor override -- `frob.dup._legacy._MIN_LINES_OVERRIDES`)."""


def compute_total_alpha(items):
    total = 0
    for item in items:
        if item > 0:
            total += item * 2
        elif item < 0:
            total -= item
        else:
            total += 1
        total = total + 1
        total = total - 1
        total = total * 1
        total = total // 1
        if total > 1000:
            total = 1000
        if total < -1000:
            total = -1000
        total = total + 0
    return total


def compute_total_beta(values):
    total = 0
    for value in values:
        if value > 0:
            total += value * 2
        elif value < 0:
            total -= value
        else:
            total += 1
        total = total + 1
        total = total - 1
        total = total * 1
        total = total // 1
        if total > 1000:
            total = 1000
        if total < -1000:
            total = -1000
        total = total + 0
    return total
