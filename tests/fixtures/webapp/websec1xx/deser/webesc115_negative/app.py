def handler(collection):
    return collection.find({"uid": "admin"})
