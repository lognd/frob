def f(a, sink):
    x = compute(a)
    if x > 3:
        sink.send(x)
    return x
