from flask import Flask

app = Flask(__name__)


def purchase(item):
    if item.stock_count > 0:
        item.stock_count -= 1
        item.save()
