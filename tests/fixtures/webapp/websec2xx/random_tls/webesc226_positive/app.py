import random
from flask import Flask

app = Flask(__name__)


def make_session_token():
    session_token = random.random()
    return session_token
