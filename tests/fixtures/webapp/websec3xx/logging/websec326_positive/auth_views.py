def login(request):
    user = authenticate(request)
    return user
