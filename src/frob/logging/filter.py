import logging


# frob:doc docs/modules/logging.md#public-api
# frob:waive COV007 reason="docs/modules/logging.md's Public API section individually \
# frob:describes this private filter and its .filter method by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:invariant INV-016
class _BelowLevelFilter(logging.Filter):
    """Pass records strictly below `below` level (used to keep stdout clean)."""

    def __init__(self, below: str) -> None:
        super().__init__()
        self._below = getattr(logging, below.upper())

    def filter(self, record: logging.LogRecord) -> bool:
        # frob:doc docs/modules/logging.md#public-api
        return record.levelno < self._below
