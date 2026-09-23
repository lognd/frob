import requests


def proxy(request):
    return requests.get(request.args["target"])
