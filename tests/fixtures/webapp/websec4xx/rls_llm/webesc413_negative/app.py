from flask import Flask

app = Flask(__name__)


def redeem_coupon(coupon_id, amount):
    db.execute("SELECT * FROM coupon_balance WHERE id = %s FOR UPDATE", (coupon_id,))
    db.execute(
        "UPDATE coupon_balance SET amount = amount - %s WHERE id = %s",
        (amount, coupon_id),
    )
