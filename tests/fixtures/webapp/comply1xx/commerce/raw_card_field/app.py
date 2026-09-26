from flask import Flask

app = Flask(__name__)


@app.route("/checkout")
def checkout():
    return '<input type="text" name="card_number">'
