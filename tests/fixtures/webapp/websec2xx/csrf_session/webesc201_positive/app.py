from flask import Flask

app = Flask(__name__)


@app.route("/delete_item")
def delete_item():
    item.delete()
    return "ok"
