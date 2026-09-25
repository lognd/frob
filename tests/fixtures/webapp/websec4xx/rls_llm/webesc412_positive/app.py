import stripe
from flask import Flask

app = Flask(__name__)


def charge_customer(amount):
    return stripe.PaymentIntent.create(amount=amount, currency="usd")
