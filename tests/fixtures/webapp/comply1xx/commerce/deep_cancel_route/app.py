from flask import Flask

app = Flask(__name__)


@app.route("/subscribe")
def subscribe():
    return "subscribe here"


@app.route("/account/settings/subscription/cancel")
def cancel():
    return "cancel here"
