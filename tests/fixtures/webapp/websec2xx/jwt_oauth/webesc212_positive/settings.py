from datetime import timedelta

SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": False,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
}
