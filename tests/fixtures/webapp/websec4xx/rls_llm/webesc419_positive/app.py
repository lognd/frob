from flask import Flask

app = Flask(__name__)


def search(query_vector):
    return index.query(vector=query_vector, top_k=5)
