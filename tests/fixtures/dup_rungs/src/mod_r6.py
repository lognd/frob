def add_twice_a(x: int) -> int:
    return x + x


def add_twice_b(x: int) -> int:
    return 2 * x


def double_plus_one(x: int) -> int:
    return 2 * x + 1


def impure_logger(x: int) -> int:
    print(x)
    return x


def impure_logger_dup(x: int) -> int:
    print(x)
    return x


def sum_twice_a(x: int, y: int) -> int:
    return (x + y) * 2


def sum_twice_b(p: int, q: int) -> int:
    return (p + q) * 2


def kwonly_subtract(*, a: int, b: int) -> int:
    return a - b


def kwonly_add(*, x: int, y: int) -> int:
    return x + y


def arity_two(x: int, y: int) -> int:
    return x + y


def arity_three(x: int, y: int, z: int) -> int:
    return x + y + z
