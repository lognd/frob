def fetch_upstream(url):
    return requests.get(url, timeout=5)
