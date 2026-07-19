def _clamp_a(value):
    if value > 100:
        value = 100
    return value


def _clamp_b(value):
    if value > 100:
        value = 100
    return value


def _clamp_c(value):
    if value > 100:
        value = 100
    return value


def normalize(value):
    return value


def public_entry(value):
    return normalize(value) + 1
