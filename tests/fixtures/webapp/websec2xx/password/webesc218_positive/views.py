def handle_delete(request, account_id):
    delete_account(account_id)
    return "ok"
