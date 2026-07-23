"""Cross-process shared/exclusive lock over a checkout's derived-state
directory (`.frob`), closing the TOCTOU window `frob.check`'s single
in-process integrity precheck (T-0603) left open (T-0859).

T-0603's `_derived_state_integrity_result` verifies `.frob`'s derived
artifacts (`cache.db`, `dup.db`, `baseline`, ...) exactly once, synchronously,
before a `run_check*` entry point dispatches its concurrent stages -- sound
against the in-process `ThreadPoolExecutor` race it was built for, but blind
to a SECOND `frob` process (a `frob serve` daemon, a parallel agent's own
`frob check` in the same checkout, a `frob mutate` run) rewriting or
corrupting the same files after the precheck passed and before a later stage
reads them. `derived_state_lock` closes that window for any two processes
that both go through it: a `frob check` run holds a SHARED lock for its
entire duration (precheck through the last stage's read), and any process
that mutates `.frob`'s derived artifacts is expected to hold the EXCLUSIVE
form while it writes -- the same shared/exclusive discipline `frob.tickets.
_store.ledger_lock` (T-0458) already uses for the ticket ledger, applied to
`.frob` itself.

Wiring the exclusive side into every current `.frob` writer (`frob mutate`,
`frob doctor`'s rebuild path, `frob.dup`/`frob.graph`'s cache rebuilders) is
tracked separately (see this ticket's Done report) -- this module only ships
the primitive and the `frob.check` shared-lock call site its own `scope`
covers; a writer that has not been wired onto the exclusive lock yet still
races the same way T-0603 disclosed, just with a narrower window (this
process's WHOLE run, not just its precheck) between fix and full coverage.
"""

from __future__ import annotations

import importlib
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from frob.logging import get_logger

# frob:waive INV006 reason="T-0859: this module's several \\bonly\\b/\\bthe\\b \
# exclusivity-vocabulary hits are source-level design-rationale prose \
# (docstrings/comments describing already-implemented internal behavior, \
# verifiable by reading the code they annotate -- e.g. which platform \
# fcntl requires, which re-entrant mode a thread already holds) rather \
# than a separate cross-module contract needing its own tracked \
# invariant, mirroring frob.check's INV006 T-0585 calibration-batch \
# waiver in src/frob/check/__init__.py"

# T-0859: `fcntl` is posix-only; `derived_state_lock` degrades to a
# documented no-op (see its docstring) on a platform without it, mirroring
# `frob.tickets._store.ledger_lock`'s T-0458 precedent.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

# frob:doc docs/modules/process.md#derived-state-lock-t-0859
#: The advisory lock file `derived_state_lock` holds, relative to a
#: checkout's `root` -- distinct from `frob.tickets._store._LOCK_REL`
#: (`.frob/tickets.lock`) so a ledger mutation and a derived-state check
#: never contend on the same file for an unrelated reason.
_LOCK_REL = Path(".frob") / "derived.lock"

# T-0859: thread-local re-entrancy bookkeeping, one entry per (path, mode)
# key, mirroring `frob.tickets._store._lock_local`'s reasoning: `flock` is
# scoped to an open file DESCRIPTION, not a process, so a naive
# "always os.open + flock" implementation would self-deadlock the moment a
# lock-holding caller in one thread invokes another lock-holding primitive
# nested inside it. A different thread or process still blocks on the real
# OS lock; only same-thread re-entry is short-circuited.
_lock_local = threading.local()


# frob:doc docs/modules/process.md#derived-state-lock-t-0859
def _derived_lock_path(root: Path) -> Path:
    """The advisory lock file path (`.frob/derived.lock`) `derived_state_lock`
    holds under checkout `root`."""
    return root / _LOCK_REL


# frob:doc docs/modules/process.md#derived-state-lock-t-0859
# frob:tests tests/unit/test_process_lock.py::TestDerivedStateLock.test_two_threads_serialize_exclusive  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestDerivedStateLock.test_shared_locks_do_not_block_each_other  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestDerivedStateLock.test_reentrant_same_mode_in_same_thread  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestDerivedStateLock.test_reentrant_opposite_mode_raises  # noqa: E501
# frob:ticket T-0859
@contextmanager
def derived_state_lock(root: Path, *, exclusive: bool) -> Iterator[None]:
    """Cross-process `flock` over checkout `root`'s derived-state directory.

    `exclusive=False` (the reader/checker form) takes a SHARED lock: any
    number of readers -- including concurrent `frob check` runs -- can hold
    it at once, but it blocks against, and is blocked by, an exclusive
    holder. `exclusive=True` (the writer form, for any process about to
    rebuild or rewrite a derived artifact under `.frob`) takes an
    EXCLUSIVE lock: it waits for every reader and every other writer to
    release first, and no reader can acquire while it is held. This is the
    same shared/exclusive discipline as a `flock(2)` reader-writer lock,
    applied to `.frob` the way `frob.tickets._store.ledger_lock` (T-0458)
    already applies a single-writer `LOCK_EX` to the ticket ledger.

    Uses `fcntl.flock` on `.frob/derived.lock` (POSIX). On a platform
    without `fcntl` this degrades to a documented no-op (logged at
    WARNING, not silently pretended to be locked) -- mirroring
    `ledger_lock`'s same fallback. Re-entrant per thread and per exact
    `exclusive` value (see `_lock_local`): a second `with
    derived_state_lock(root, exclusive=X)` in the SAME thread, requesting
    the SAME mode, is a no-op re-entry; requesting the OPPOSITE mode while
    already holding one from the same thread is refused up front (a
    same-thread exclusive-under-shared or shared-under-exclusive upgrade/
    downgrade is not supported and would either deadlock against the
    thread's own held lock or silently violate the mode it already holds).
    """
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "process: derived_state_lock: fcntl unavailable on this "
            "platform, lock is a NO-OP (mirrors ledger_lock's T-0458 "
            "fallback) -- concurrent frob processes are NOT serialized here"
        )
        yield
        return

    path = _derived_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    maybe_held: dict[str, tuple[int, bool, int]] | None = getattr(
        _lock_local, "held", None
    )
    held: dict[str, tuple[int, bool, int]] = (
        maybe_held if maybe_held is not None else {}
    )
    if maybe_held is None:
        _lock_local.held = held

    entry = held.get(key)
    if entry is not None:
        fd, held_exclusive, depth = entry
        if held_exclusive != exclusive:
            raise RuntimeError(
                f"derived_state_lock: {path} already held in "
                f"{'exclusive' if held_exclusive else 'shared'} mode by "
                f"this thread; cannot re-enter as "
                f"{'exclusive' if exclusive else 'shared'} (upgrade/"
                "downgrade is not supported)"
            )
        held[key] = (fd, held_exclusive, depth + 1)
        try:
            yield
        finally:
            fd, held_exclusive, depth = held[key]
            if depth <= 1:
                del held[key]
            else:
                held[key] = (fd, held_exclusive, depth - 1)
        return

    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    held[key] = (fd, exclusive, 1)
    _log.debug(
        "process: derived_state_lock acquired (%s, exclusive=%s)",
        path,
        exclusive,
    )
    try:
        yield
    finally:
        del held[key]
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug(
            "process: derived_state_lock released (%s, exclusive=%s)",
            path,
            exclusive,
        )


__all__ = ["derived_state_lock"]
