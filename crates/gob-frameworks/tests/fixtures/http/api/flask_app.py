from flask import Flask

app = Flask(__name__)


@app.route('/api/items', methods=['GET', 'PUT'])
def items():
    return ''


@app.delete('/api/items/<int:item_id>')
def drop(item_id):
    return ''
