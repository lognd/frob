from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/users/<user_id>")
def get_user(user_id):
    user = User.objects.get(id=user_id)
    return jsonify(user.__dict__)
