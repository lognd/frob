DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "app",
        "OPTIONS": {"sslmode": "require"},
    }
}
# Storage is encrypted at rest via the managed provider.
