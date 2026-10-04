import os


def apply(fn, fns):
    fn()
    fns[0]()
    return os.getcwd()
