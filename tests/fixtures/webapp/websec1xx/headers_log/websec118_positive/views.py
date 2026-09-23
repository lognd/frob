def build_avatar_url(request):
    return "https://" + request.args["host"] + "/avatar.png"
