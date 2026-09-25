from flask import Flask

app = Flask(__name__)


def purchase(item_id):
    if item.stock_count > 0:
        item = Item.objects.select_for_update().get(id=item_id)
        item.stock_count -= 1
        item.save()
