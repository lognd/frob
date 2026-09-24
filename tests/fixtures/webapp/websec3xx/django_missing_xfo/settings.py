"""Fixture Django settings missing X_FRAME_OPTIONS (T-5325 negative control)."""

SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
CSP_DEFAULT_SRC = ("'self'",)
SECURE_REFERRER_POLICY = "no-referrer"
