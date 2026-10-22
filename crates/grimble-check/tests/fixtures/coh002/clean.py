def f(a, sink):
    if a > 3:
        sink.send(a)
    x = compute(a)
    if x > 3:
        log(x)
    return x
