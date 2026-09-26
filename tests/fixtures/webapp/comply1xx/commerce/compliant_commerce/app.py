from flask import Flask

app = Flask(__name__)


@app.route("/subscribe")
def subscribe():
    return "subscribe here"


@app.route("/cancel")
def cancel():
    return "cancel here"


@app.route("/checkout")
def checkout():
    return "<script>Stripe('pk_test'); var elements = stripe.elements(); elements.create('card');</script>"
