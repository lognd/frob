from __future__ import annotations

import logging


# frob:doc docs/index.md#public-api
class BelowLevelFilter(logging.Filter):
    """Pass only records with levelno strictly below the configured threshold."""

    def __init__(self, below: str = "WARNING") -> None:
        super().__init__()
        # T-3277: logging.getLevelNamesMapping() is a real dict lookup, not
        # a runtime-resolved attribute indirection (OPAQUE001's
        # python:runtime:getattr-dynamic-name pattern) -- `getattr(logging,
        # below.upper(), ...)` reads as a dynamic capability probe even
        # though `below` is always one of the fixed stdlib level names.
        self._below = logging.getLevelNamesMapping().get(below.upper(), logging.WARNING)

    def filter(self, record: logging.LogRecord) -> bool:
        # frob:doc docs/index.md#public-api
        return record.levelno < self._below
