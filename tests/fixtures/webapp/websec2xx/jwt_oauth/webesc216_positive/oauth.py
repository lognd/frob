def authorize_url(client_id, state):
    return f"https://auth.example.com/authorize?response_type=code&client_id={client_id}&state={state}"
