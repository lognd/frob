from flask import Flask, session, make_response
from flask_login import login_required

app = Flask(__name__)


@app.route("/account")
@login_required
def account():
    resp = make_response("secret account data")
    resp.headers["Cache-Control"] = "no-store"
    return resp
