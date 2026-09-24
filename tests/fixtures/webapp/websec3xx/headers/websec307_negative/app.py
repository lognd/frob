from flask import Flask

app = Flask(__name__)


@app.route("/api/data")
def data():
    resp = make_response()
    resp.headers["Access-Control-Allow-Origin"] = "https://trusted.example.com"
    return resp
