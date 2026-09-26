from flask import Flask

app = Flask(__name__)


@app.route('/gdpr/delete', methods=['POST'])
def gdpr_delete():
    return 'ok'
