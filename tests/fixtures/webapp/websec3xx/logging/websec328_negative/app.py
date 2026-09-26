def handle(request):
    logger.info("processing request for user %s", request.form["user_id"])
