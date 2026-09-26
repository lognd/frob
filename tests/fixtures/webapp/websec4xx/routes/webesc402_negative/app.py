from flask import Flask
from flask_login import login_required

app = Flask(__name__)


@app.route("/admin/users")
@login_required
def admin_users():
    return list_all_users()
