import pickle


def handler(raw_bytes):
    return pickle.loads(raw_bytes)
