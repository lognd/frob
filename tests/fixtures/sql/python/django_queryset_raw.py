"""Positive control: Django QuerySet.raw() with a literal SQL string.

frob:ticket T-5334
"""


def fetch_active_users(queryset):
    """Run a literal raw SQL query through Django's QuerySet.raw().

    frob:ticket T-5334
    """
    return queryset.raw("SELECT * FROM users WHERE active = 1")
