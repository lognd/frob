from flask import Flask, request

app = Flask(__name__)


@app.route("/users/<user_id>", methods=["PATCH"])
def update_user(user_id):
    allowed = {"display_name": request.json.get("display_name")}
    return User.objects.update(**allowed)
