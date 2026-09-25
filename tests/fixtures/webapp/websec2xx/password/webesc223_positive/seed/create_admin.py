def seed_admin():
    User.objects.create(username="admin", password="admin")
