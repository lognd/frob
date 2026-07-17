def combine_a(x, y, z):
    p = x + y
    q = y + z
    return p + q


def combine_b(x, y, z):
    q = y + z
    p = x + y
    return p + q


def unrelated_calc(a, b):
    r = a * b
    return r
