import secrets
from flask import Flask

app = Flask(__name__)


def make_session_token():
    session_token = secrets.token_urlsafe()
    return session_token
