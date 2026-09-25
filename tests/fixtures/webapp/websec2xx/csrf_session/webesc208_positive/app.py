from flask import Flask

app = Flask(__name__)


def logout(user):
    return "bye"
