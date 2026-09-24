from flask import request


def handler(collection):
    return collection.find(request.json)
