"""Flask WEBSEC401 fixture: one owner-checked route (clean), one that
skips the owner check (planted finding).

frob:ticket T-5356
"""
from flask import Flask, g

app = Flask(__name__)


@app.route("/orders/<order_id>")
def get_order(order_id):
    """Clean: filters the order by the authenticated user's own id."""
    return Order.query.filter_by(id=order_id, user_id=g.user.id).first()


@app.route("/orders/<order_id>/unsafe")
def get_order_unsafe(order_id):
    """Planted finding: fetches the order with no owner correlation at all."""
    return Order.query.filter_by(id=order_id).first()
