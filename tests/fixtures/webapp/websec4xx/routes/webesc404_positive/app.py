from flask import Flask, request

app = Flask(__name__)


@app.route("/users/<user_id>", methods=["PATCH"])
def update_user(user_id):
    return User.objects.update(**request.json)
