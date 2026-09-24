def handler(conn, username):
    return conn.search_s("dc=example,dc=com", 2, "(uid=" + username + ")")
