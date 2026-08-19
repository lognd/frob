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

from __future__ import annotations

import contextlib
import logging
import os
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
# frob:invariant INV-038
# frob:ticket T-0585
# invariant spec: [INV-038](invariants/INV-038.md)
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


@contextlib.contextmanager
# frob:doc docs/modules/logging.md#public-api
# frob:ticket T-2582
# frob:tests \
# tests/unit/test_logging_quiet.py::TestQuietQueryStdout.test_quiets_by_default \
# kind="unit"
# frob:tests tests/unit/test_logging_quiet.py::TestQuietQueryStdout.test_frob_verbose_env_var_restores_full_chatter kind="unit"  # noqa: E501
# frob:tests \
# tests/unit/test_logging_quiet.py::TestQuietQueryStdout.test_restores_on_exception \
# kind="unit"
def quiet_query_stdout() -> Iterator[None]:
    """Quiet stdout-bound DEBUG/INFO logs by default for a human-mode query
    command; `FROB_VERBOSE=1` opts back into the full diagnostic stream.

    T-2582: `--json` mode was always wrapped in `quiet_stdout_logs()`
    (protecting the machine-readable payload), but the human-mode path
    used `contextlib.nullcontext()` -- backwards, since a human invoking
    `frob explore xref foo` gets thousands of `gitio: spawning`/`parse
    cache hit` lines ahead of a 13-line answer. Diagnostics belong off the
    default stdout view in BOTH modes; this is the one shared default the
    8 affected runners (`debt`/`deprecated`/`exports`/`fleet`/`gitlog`/
    `mutate`/`outline`/`xref`) now call unconditionally instead of gating
    `quiet_stdout_logs()` on `cfg.<name>_json`, so a ninth runner does not
    need its own copy of this branch next time. `FROB_VERBOSE=1` is the
    escape hatch (an env var rather than a new per-command CLI flag,
    since `--verbose` plumbing here would need a change to
    `AppConfig`/`_config_external.py`'s field registries, both under a
    live lease from a concurrent ticket at the time this landed) -- it
    restores the FULL chatter (equivalent to `nullcontext()`), never a
    lossy partial view; a debugging session that needs
    `gitio: spawning`/`parse cache hit` output still gets it verbatim.
    """
    # frob:waive SEC110 reason="FROB_VERBOSE is a local verbosity toggle (log-chatter \
    # on/off), not a secret source -- nothing sensitive flows through this read"
    if os.environ.get("FROB_VERBOSE") == "1":
        yield
        return
    with quiet_stdout_logs():
        yield


@contextlib.contextmanager
# frob:doc docs/modules/logging.md#public-api
# frob:ticket T-0768
def logger_levels(levels: dict[str, int]) -> Iterator[None]:
    """Set each named logger to its mapped level for the duration of the block.

    Backs `frob ticket`'s default-quiet dispatch (T-0768): unlike the
    handler-wide `stdout_log_level`, this discriminates BY LOGGER, so a
    runner whose user-facing output channel is its own module logger's
    INFO (`frob.app.ticket_runner`) can clamp the rest of the `frob` tree
    to WARNING without swallowing its own output. Plain save/restore --
    callers own a single top-level CLI invocation, so no T-0125 reentrancy
    machinery is needed. A logger whose saved level was NOTSET is restored
    to NOTSET (inheritance), not to its effective level.
    """
    saved = {name: logging.getLogger(name).level for name in levels}
    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)
    try:
        yield
    finally:
        for name, level in saved.items():
            logging.getLogger(name).setLevel(level)
