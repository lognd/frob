from flask import Flask
app = Flask(__name__)

@app.route("/privacy")
def privacy():
    return "privacy policy"

@app.route("/terms")
def terms():
    return "terms of service"

@app.route("/accessibility")
def accessibility():
    return "accessibility statement"
