def download(request, response):
    response.headers["Content-Disposition"] = f"attachment; filename={request.args['name']}"
