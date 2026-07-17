"""Temporarily silence stdout-bound INFO/DEBUG logging (docs/lang.md).

`frob.lang.parse_file` logs at INFO/DEBUG on every parse (the LOG EVERYTHING
convention) -- the old `frob.ast` wrappers it replaces logged nothing at
all. Any CLI runner that prints a machine-readable payload (`--json`) to
stdout after calling into `frob.lang` needs those log lines kept off stdout
for the run, or they corrupt the payload. `frob.app.check_runner` solved
this once already for the check pipeline; this is that same mechanism
pulled out so `map`/`outline`/`xref` runners can reuse it instead of each
re-deriving it.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Iterator


@contextlib.contextmanager
def quiet_stdout_logs() -> Iterator[None]:
    """Raise stdout log handlers to WARNING for the duration of the block."""
    root_logger = logging.getLogger()
    stdout_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
    ]
    saved = [h.level for h in stdout_handlers]
    for h in stdout_handlers:
        h.setLevel(logging.WARNING)
    try:
        yield
    finally:
        for h, level in zip(stdout_handlers, saved, strict=True):
            h.setLevel(level)
