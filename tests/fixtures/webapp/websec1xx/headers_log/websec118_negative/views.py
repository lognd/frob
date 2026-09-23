from urllib.parse import quote


def build_avatar_url(request):
    return "https://" + quote(request.args["host"]) + "/avatar.png"
