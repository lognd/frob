from flask import Flask

app = Flask(__name__)


@app.route('/items')
def list_items():
    return render_template('items.html')
