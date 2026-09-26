from flask import Flask, request
from flask_limiter import Limiter

app = Flask(__name__)
limiter = Limiter(app)


@app.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    return authenticate(request.form["username"], request.form["password"])
