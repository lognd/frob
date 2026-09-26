from flask import Flask

app = Flask(__name__)


@app.route("/orders/<order_id>")
def get_order(order_id):
    return Order.query.filter_by(id=order_id).first()
