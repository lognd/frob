"""SYNTHETIC FIXTURE (T-4113, SYS111 must-fire): a stub outbound call site
whose connection target is a hardcoded literal host, with no config-field
binding -- not real frob code, never imported by the package."""

import requests  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]


def fetch_media():
    """Stub call: connects to a literal, unconstrained host."""
    return requests.get("https://media.example.com/asset")
