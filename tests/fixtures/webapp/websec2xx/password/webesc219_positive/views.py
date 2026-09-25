def reset_password(request, user, new_password):
    user.set_password(new_password)
    user.save()
