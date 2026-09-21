"""SYNTHETIC FIXTURE (T-4113, SYS111 must-stay-quiet): a stub outbound call
site whose connection target is read from a config field -- not real frob
code, never imported by the package."""

import requests  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]

from . import config


def fetch_media():
    """Stub call: connects to a config-bound, allowlisted host."""
    return requests.get(config.MEDIA_HOST_URL)
