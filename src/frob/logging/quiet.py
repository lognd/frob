"""Temporarily silence stdout-bound INFO/DEBUG logging (docs/modules/lang.md).

`frob.lang.parse_file` logs at INFO/DEBUG on every parse (the LOG EVERYTHING
convention) -- the retired per-language wrappers it replaces logged nothing
at all. Any CLI runner that prints a machine-readable payload (`--json`) to
stdout after calling into `frob.lang` needs those log lines kept off stdout
for the run, or they corrupt the payload. `frob.app.check_runner` solved
this once already for the check pipeline; this is that same mechanism
pulled out so `map`/`outline`/`xref` runners can reuse it instead of each
re-deriving it.

T-0125: `quiet_stdout_logs` mutates the shared, process-global root logger's
stdout handler level. Two unrelated callers (e.g. `frob.arch.analyze_project`
and `frob.dup.find_duplicates`, invoked concurrently by `frob check`'s
`ThreadPoolExecutor`) can race the save/restore: if thread B enters after
thread A has already lowered the handler to WARNING, B's "saved" level IS
WARNING, and B's restore leaves the handler stuck at WARNING forever after
both return cleanly -- no exception, no trace, just silently swallowed
INFO-level logs downstream. The fix is a module-level lock plus a reentrancy
depth counter: only the outermost caller (across all threads) saves the
pre-existing level and only the outermost caller restores it; nested/
concurrent callers just bump the depth. A per-thread/contextvars filter
would also fix this, but that changes what "stdout log level" even means
(per-thread vs process-wide) for zero benefit here -- the depth-counter
fix keeps the existing process-wide-mute semantics that every caller (and
`frob check`'s belt-and-suspenders `_restore_stdout_log_levels`, kept as
defense in depth) already assumes.
"""

# frob:invariant INV-038
from __future__ import annotations

import contextlib
import logging
import sys
import threading
from collections.abc import Iterator

_lock = threading.Lock()
_depth = 0
_saved_levels: list[int] | None = None


def _stdout_stream_handlers() -> list[logging.StreamHandler]:
    """Return the root logger's `StreamHandler`s writing to `sys.stdout`."""
    root_logger = logging.getLogger()
    return [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
    ]


@contextlib.contextmanager
# frob:doc docs/modules/logging.md#public-api
def stdout_log_level(level: int) -> Iterator[None]:
    """Set every stdout-bound `StreamHandler` to `level` for the duration of the block.

    Backs `frob check`'s `-v`/`-vv` verbosity gating (T-0202): the shared
    root-logger stdout handler defaults to DEBUG (`config.toml`), so every
    per-file/per-symbol DEBUG/INFO log line prints at default verbosity
    unless a caller narrows the handler first. Unlike `quiet_stdout_logs`,
    this is a plain save/restore -- callers own a single top-level CLI
    invocation (not concurrent library code), so the reentrancy/thread-
    safety machinery `quiet_stdout_logs` needs for T-0125 is not needed
    here. Do not nest this with `quiet_stdout_logs`; a caller wants one or
    the other, never both.
    """
    handlers = _stdout_stream_handlers()
    saved = [h.level for h in handlers]
    for h in handlers:
        h.setLevel(level)
    try:
        yield
    finally:
        for h, saved_level in zip(handlers, saved, strict=True):
            h.setLevel(saved_level)


@contextlib.contextmanager
# frob:doc docs/modules/logging.md#public-api
def quiet_stdout_logs() -> Iterator[None]:
    """Raise stdout log handlers to WARNING for the duration of the block.

    Reentrant and thread-safe (T-0125): a module-level lock plus depth
    counter ensures only the outermost caller across all threads saves
    and restores the pre-existing handler levels, so concurrent or nested
    callers can never race each other into leaving the handler stuck.
    """
    global _depth, _saved_levels
    stdout_handlers = _stdout_stream_handlers()
    with _lock:
        if _depth == 0:
            _saved_levels = [h.level for h in stdout_handlers]
            for h in stdout_handlers:
                h.setLevel(logging.WARNING)
        _depth += 1
    try:
        yield
    finally:
        with _lock:
            _depth -= 1
            if _depth == 0 and _saved_levels is not None:
                for h, level in zip(stdout_handlers, _saved_levels, strict=True):
                    h.setLevel(level)
                _saved_levels = None
