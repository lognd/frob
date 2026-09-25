from datetime import timedelta

SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": True,
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}
