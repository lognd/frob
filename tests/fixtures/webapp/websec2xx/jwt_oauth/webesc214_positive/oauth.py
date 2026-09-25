def authorize_url(client_id, challenge):
    return f"https://auth.example.com/authorize?response_type=code&client_id={client_id}&code_challenge={challenge}"
