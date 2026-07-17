import logging


# frob:doc docs/modules/logging.md#public-api
class BelowLevelFilter(logging.Filter):
    """Pass records strictly below `below` level (used to keep stdout clean)."""

    def __init__(self, below: str) -> None:
        super().__init__()
        self._below = getattr(logging, below.upper())

    def filter(self, record: logging.LogRecord) -> bool:
        # frob:doc docs/modules/logging.md#public-api
        return record.levelno < self._below
