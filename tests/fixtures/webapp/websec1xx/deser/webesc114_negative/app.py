def handler(conn):
    return conn.search_s("dc=example,dc=com", 2, "(uid=admin)")
