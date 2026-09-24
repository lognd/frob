import pickle


def handler():
    return pickle.loads(b"\x80\x04N.")
