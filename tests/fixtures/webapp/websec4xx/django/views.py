"""Django WEBSEC401 fixture: one owner-checked view (clean), one that
skips the owner check (planted finding).

frob:ticket T-5356
"""


def get_profile(request, profile_id):
    """Clean: get_object_or_404 filtered by the authenticated user."""
    return get_object_or_404(Profile, id=profile_id, owner=request.user)


def get_profile_unsafe(request, profile_id):
    """Planted finding: no auth-identity reference anywhere in the body."""
    return get_object_or_404(Profile, id=profile_id)
