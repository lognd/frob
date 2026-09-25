from flask import Flask, request

app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    return 'ok'
