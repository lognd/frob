def handle_delete(request, account_id):
    if not request.user.email_verified:
        return "forbidden"
    delete_account(account_id)
    return "ok"
