from urllib.parse import quote


def handle(request, response):
    response.setHeader("X-Redirect-To", quote(request.args["next"]))
