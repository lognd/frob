def f(a, b, **kw):
    x = a + 1
    y = b
    y = x
    self.v = x
    z = self.v
    setattr(a, "k", y)
    w = a.k
    g(**kw)
    k = kw
    c = lambda: x + y
    if x:
        y = 2
    else:
        y = 3
    for i in a:
        y = y + i
    return y + z + w
