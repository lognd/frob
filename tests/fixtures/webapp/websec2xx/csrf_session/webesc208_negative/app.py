from flask import Flask, session

app = Flask(__name__)


def logout(user):
    session.flush()
    return "bye"
