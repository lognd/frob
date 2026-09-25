from flask import Flask, request

app = Flask(__name__)

db.session.query(User).all()


@app.route("/check")
def check():
    if request.cookies.get("session_id") == "expected-token":
        return "ok"
    return "no"
