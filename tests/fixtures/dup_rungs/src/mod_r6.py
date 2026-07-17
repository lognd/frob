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
