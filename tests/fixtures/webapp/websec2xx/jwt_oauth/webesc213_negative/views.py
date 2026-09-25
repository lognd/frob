def auth_header(token):
    headers = {"Authorization": f"Bearer {token}"}
    return headers
