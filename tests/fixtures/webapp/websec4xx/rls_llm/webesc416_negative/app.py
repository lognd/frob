from flask import Flask

app = Flask(__name__)


def transfer_funds(from_account, to_account, amount):
    if not user_confirmation_received():
        raise PermissionError('confirm the transfer first')
    ledger.move(from_account, to_account, amount)
    return 'done'
