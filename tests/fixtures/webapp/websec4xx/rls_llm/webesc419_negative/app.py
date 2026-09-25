from flask import Flask

app = Flask(__name__)


def search(query_vector, user_id):
    return index.query(vector=query_vector, top_k=5, filter={"user_id": user_id})
