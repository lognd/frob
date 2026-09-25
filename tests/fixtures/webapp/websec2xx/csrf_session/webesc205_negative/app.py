from flask import Flask, session

app = Flask(__name__)


def login(user):
    session['user_id'] = user.id
    session.regenerate()
    return 'ok'
