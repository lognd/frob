from flask import Flask, request

app = Flask(__name__)


@app.route('/check')
def check():
    if request.cookies.get('session_id') == 'expected-token':
        return 'ok'
    return 'no'
