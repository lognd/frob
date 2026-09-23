from urllib.parse import quote


def download(request, response):
    response.headers["Content-Disposition"] = f"attachment; filename={quote(request.args['name'])}"
