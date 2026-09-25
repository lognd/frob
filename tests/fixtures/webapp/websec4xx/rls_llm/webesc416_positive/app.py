from flask import Flask

app = Flask(__name__)


def transfer_funds(from_account, to_account, amount):
    ledger.move(from_account, to_account, amount)
    return 'done'
