"""Fixture Django settings with every T-5325 security header setting present."""

SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"
CSP_DEFAULT_SRC = ("'self'",)
SECURE_REFERRER_POLICY = "no-referrer"
