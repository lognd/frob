from flask import Flask

app = Flask(__name__)


@app.route("/privacy")
def privacy():
    return "privacy policy"
