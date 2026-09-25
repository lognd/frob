import jwt

jwt.decode(token, key, algorithms=["HS256"], audience="svc")
