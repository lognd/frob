from flask import Flask

app = Flask(__name__)


@app.route("/admin/users")
def admin_users():
    return list_all_users()
