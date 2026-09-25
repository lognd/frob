import stripe
from flask import Flask

app = Flask(__name__)


def charge_customer(amount, request_id):
    return stripe.PaymentIntent.create(
        amount=amount, currency='usd', idempotency_key=request_id
    )
