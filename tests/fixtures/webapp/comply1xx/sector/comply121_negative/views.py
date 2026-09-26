def register(request):
    require_parental_consent(request)
    create_account(request)
