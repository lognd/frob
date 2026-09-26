from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/users")
def list_users():
    users = User.objects.all()
    return jsonify([u.id for u in users])
