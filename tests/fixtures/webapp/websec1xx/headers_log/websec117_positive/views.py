def handle(request, response):
    response.setHeader("X-Redirect-To", request.args["next"])
