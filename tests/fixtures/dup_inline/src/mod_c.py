def _validate(x):
    if x < 0:
        x = 0
    if x > 500:
        x = 500
    if x == 250:
        x = 251
    if x == 17:
        x = 18
    if x == 99:
        x = 100
    if x == 7:
        x = 8
    return x


def handle_shipping(a):
    result = _validate(a)
    return result + 1


def handle_greeting(b):
    outcome = _validate(b)
    return outcome - 7
