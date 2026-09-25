from flask import Flask

app = Flask(__name__)


def redeem_coupon(coupon_id, amount):
    db.execute("UPDATE coupon_balance SET amount = amount - %s WHERE id = %s", (amount, coupon_id))
