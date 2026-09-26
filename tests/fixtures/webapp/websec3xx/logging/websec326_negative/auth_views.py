def login(request):
    user = authenticate(request)
    logger.info("login attempt for user %s", user)
    return user
