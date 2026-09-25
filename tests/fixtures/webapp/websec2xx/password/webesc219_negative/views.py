def reset_password(request, user, new_password):
    if is_pwned(new_password):
        raise ValueError("password appears in a known breach corpus")
    user.set_password(new_password)
    user.save()
