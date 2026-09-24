from flask import Flask, session
from flask_login import login_required

app = Flask(__name__)


@app.route("/account")
@login_required
def account():
    return "secret account data"
