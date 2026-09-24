from flask import Flask

app = Flask(__name__)


@app.route("/api/account")
def account():
    resp = make_response()
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp
