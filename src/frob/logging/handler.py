"""Log handlers that resolve their target stream lazily, at emit time.

WHY: `logging.config.dictConfig` resolves `ext://sys.stdout`/`ext://sys.stderr`
once, at configuration time, and binds the resulting stream OBJECT into the
`StreamHandler` permanently. Because frob's root logger is configured lazily
on the first `get_logger()` call and cached process-wide
(`frob.logging.logger._initialized`), whichever stream object happened to be
`sys.stdout`/`sys.stderr` at that moment -- often a pytest `capsys`/`capfd`
substitute stream -- stays bound forever. Once that substitute stream is
closed at the end of its owning test, every later `logging.Handler.emit()`
call raises `ValueError: I/O operation on closed file`, which
`logging.Handler.handleError` reports as its own "--- Logging error ---"
traceback written to whatever the CURRENT `sys.stderr` is (polluting an
unrelated test's captured output, T-1385 symptom A) or, under pytest-xdist,
repeats until the worker process dies (T-1385 symptom B).

The handlers below never cache the stream object: `stream` is a property
that re-reads `sys.stdout`/`sys.stderr` on every access, so each `emit()`
call writes to whichever stream is current at that moment, never a stale
captured one.
"""

from __future__ import annotations

import logging
import sys
from typing import TextIO


# frob:doc docs/modules/logging.md#public-api
class _LazyStdoutHandler(logging.StreamHandler):
    """StreamHandler that re-resolves sys.stdout on every emit, not at bind time."""

    def __init__(self) -> None:
        """Bind sys.stdout to satisfy the base constructor; reads use the property."""
        super().__init__(sys.stdout)

    @property
    def stream(self) -> TextIO:  # type: ignore[override]
        """Return the CURRENT sys.stdout, never one captured at config time."""
        return sys.stdout

    @stream.setter
    def stream(self, value: TextIO) -> None:
        """Discard the assignment; the stream is always resolved live via the getter."""


# frob:doc docs/modules/logging.md#public-api
class _LazyStderrHandler(logging.StreamHandler):
    """StreamHandler that re-resolves sys.stderr on every emit, not at bind time."""

    def __init__(self) -> None:
        """Bind sys.stderr to satisfy the base constructor; reads use the property."""
        super().__init__(sys.stderr)

    @property
    def stream(self) -> TextIO:  # type: ignore[override]
        """Return the CURRENT sys.stderr, never one captured at config time."""
        return sys.stderr

    @stream.setter
    def stream(self, value: TextIO) -> None:
        """Discard the assignment; the stream is always resolved live via the getter."""
