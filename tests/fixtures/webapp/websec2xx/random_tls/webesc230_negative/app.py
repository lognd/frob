from flask import Flask
from flask_limiter import Limiter

app = Flask(__name__)
limiter = Limiter(app)


def login(user):
    return 'ok'
