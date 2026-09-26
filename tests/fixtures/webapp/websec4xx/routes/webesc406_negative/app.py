from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/users")
def list_users():
    page = int(request.args.get("page", 1))
    users = User.objects.all().paginate(page=page, per_page=20)
    return jsonify([u.id for u in users])
