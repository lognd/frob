import secrets


def seed_admin():
    User.objects.create(username="admin", password=secrets.token_urlsafe(32))
