import stripe
from flask import Flask, request

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    event = stripe.Webhook.construct_event(
        request.data, request.headers.get('Stripe-Signature'), 'whsec_x',
    )
    return 'ok'
