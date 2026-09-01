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

import errno
import importlib
import os
import threading
import time
from pathlib import Path
from types import ModuleType

from frob.logging import get_logger

# T-1201/T-3596/T-3628 split re-export shim, one consolidated block
# (T-3645: a prior split left these scattered across the file).
from frob.process._derived_lock import (  # noqa: F401 -- T-1201 split
    DerivedStateLockUnavailable,
    _canonical_registry_key,
    _derived_lock_path,  # noqa: F401 -- T-3596
    _process_already_holds,  # noqa: F401 -- T-3596
    _worker_inherits_hold,  # noqa: F401 -- T-3596
    derived_state_lock,
    derived_state_write_lock,
    held_registry_keys,
)
from frob.process._lock_msvcrt import (  # noqa: F401 -- T-1201 split
    _msvcrt_acquire_blocking,
    _msvcrt_release,
)

# T-0859/T-2934: `fcntl` is posix-only. `derived_state_lock` used to
# degrade to an unconditional, unbounded, logged-but-silent no-op on any
# platform without it -- the same PLATFORM001-shaped bug T-2918 fixed in
# `frob.app.ticket_runner._rapid_sweep._baseline_lock`. Now tries
# `msvcrt` (Windows) as a second real backend, and raises
# `DerivedStateLockUnavailable` (a loud refusal) only when NEITHER
# primitive exists.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

msvcrt: ModuleType | None
try:
    msvcrt = importlib.import_module("msvcrt")
except ImportError:  # pragma: no cover -- windows-only in this repo's CI
    msvcrt = None

_log = get_logger(__name__)


#: T-3577: ceiling `_msvcrt_acquire_blocking`'s poll loop retries against,
#: in seconds, before raising `PortableLockUnavailable` instead of retrying
#: forever. `fcntl.flock` without `LOCK_NB` genuinely blocks indefinitely
#: on POSIX, but that is safe there because re-locking the SAME fd (the
#: shape every call site in this codebase uses) is a no-op -- `msvcrt.
#: locking` has no such same-fd/same-process reentrancy (T-3577's own
#: measured finding: none of the ported call sites -- `frob.tickets.
#: _store`/`_land`/`_leases`/`_land_queue`/`_mutation_sweep_queue`/
#: `_new_renumber`/`_land_git_ops`, `frob.serve._socketd`, `frob.testing.
#: _coverage_wait` -- carry `derived_state_lock`'s own same-process
#: reentrancy guard), so a nested same-process re-acquire of the same lock
#: retries against itself FOREVER on Windows with no bound at all. Chosen
#: generous (well above any legitimate cross-process contention this
#: codebase's own locks are held for) so a genuinely slow but healthy
#: contender never trips it -- this exists to convert an indefinite,
#: silent hang into a loud, bounded failure, not to police normal
#: contention latency.
_MSVCRT_BLOCKING_ACQUIRE_CEILING_S = 120.0


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_windows_branch_selected_when_fcntl_absent  # noqa: E501
# frob:ticket T-3506
class PortableLockUnavailable(RuntimeError):
    """T-3506: raised by `portable_flock_acquire` when neither `fcntl`
    (POSIX) nor `msvcrt` (Windows) is importable on this platform -- the
    SHARED base every per-module `*LockUnavailable` (`DerivedStateLock
    Unavailable` here, and its now-ported siblings in `frob.tickets.
    _store`/`_new_renumber`/`_land`/`_leases`/`_land_queue`/
    `_mutation_sweep_queue`, `frob.serve._socketd`, `frob.app.
    ticket_runner._rapid_sweep`, `frob.testing._coverage_wait`)
    previously re-derived its own `neither primitive is available` guard
    around. Call sites that want their own historically-named exception
    (for a stable public error surface / existing tests) still define
    their own subclass and raise IT after calling `lock_backend_
    available()` themselves; call sites with no such history can let
    this propagate directly."""


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_windows_branch_selected_when_fcntl_absent  # noqa: E501
# frob:ticket T-3506
def lock_backend_available() -> bool:
    """Whether a real advisory-lock primitive exists on this platform at
    all (`fcntl` on POSIX, `msvcrt` on Windows) -- the guard every lock
    call site across this codebase used to re-derive as its own `if
    fcntl is None and msvcrt is None:` check before raising its own
    loud, module-specific unavailable-error. Never a silent-degrade
    signal by itself: a caller that gets `False` back is expected to
    raise (or propagate `PortableLockUnavailable`), never to proceed
    unlocked (T-2934/T-2918's PLATFORM001 doctrine)."""
    return fcntl is not None or msvcrt is not None


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_posix_blocking_acquire_release_round_trips  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_posix_nonblocking_contended_returns_false  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_windows_branch_selected_when_fcntl_absent  # noqa: E501
# frob:ticket T-3506
def portable_flock_acquire(
    fd: int,
    *,
    exclusive: bool,
    blocking: bool = True,
    timeout: float | None = None,
) -> bool:
    """Acquire an advisory lock on open file descriptor `fd` -- the ONE
    shared dual-path (`fcntl.flock` on POSIX / `msvcrt.locking` on
    Windows) primitive `derived_state_lock` used to hand-roll on its
    own, extracted (T-3506) so every OTHER lock call site in this
    codebase (`frob.tickets._store`/`_new_renumber`/`_land`/`_leases`/
    `_land_queue`/`_mutation_sweep_queue`/`_land_git_ops`, `frob.serve.
    _socketd`, `frob.app.ticket_runner._rapid_sweep`, `frob.testing.
    _coverage_wait`) can stop re-deriving its OWN msvcrt branch.

    Three acquire shapes, matching the three this codebase's pre-T-3506
    call sites actually used (never invented beyond that -- this ticket
    does not change lock semantics, only shares the primitive behind
    them):

    - `blocking=True, timeout=None` (the default): blocks until
      acquired, exactly like bare `fcntl.flock(fd, LOCK_EX)` (no
      `LOCK_NB`) -- on Windows, `_msvcrt_acquire_blocking`'s poll loop,
      bounded at `_MSVCRT_BLOCKING_ACQUIRE_CEILING_S` (T-3577: `msvcrt`
      has no same-process reentrancy the way POSIX same-fd re-flock does,
      so this shape raises rather than hanging forever on a nested
      same-process re-acquire -- see that constant's own docstring).
      Always returns True (never returns False; only raises).
    - `blocking=False, timeout=None`: ONE non-blocking attempt, exactly
      like `fcntl.flock(fd, LOCK_EX | LOCK_NB)` -- returns True if
      acquired, False if already held by someone else (never raises for
      contention; an `OSError` for any OTHER reason still propagates).
      On Windows, one `msvcrt.locking(fd, LK_NBLCK, 1)` attempt.
    - `blocking=True, timeout=<seconds>`: polls (matching `_baseline_
      lock`'s T-2918 shape) until acquired or `timeout` elapses, then
      returns False -- never raises on a timeout.

    `exclusive=False` (SHARED) is only meaningful on POSIX: `msvcrt` has
    no shared/read-lock mode at all, so the Windows backend always takes
    an EXCLUSIVE lock regardless of `exclusive` (the same documented,
    deliberate conservative-concurrency tradeoff `derived_state_lock`'s
    own docstring already describes).

    Raises `PortableLockUnavailable` if neither `fcntl` nor `msvcrt` is
    importable on this platform -- callers that want their own named
    exception should check `lock_backend_available()` first and raise
    that instead, before ever reaching this call."""
    if fcntl is not None:
        return _portable_flock_acquire_posix(
            fd, exclusive=exclusive, blocking=blocking, timeout=timeout
        )
    if msvcrt is not None:  # pragma: no cover -- windows-only
        return _portable_flock_acquire_windows(fd, blocking=blocking, timeout=timeout)
    raise PortableLockUnavailable(
        f"process: portable_flock_acquire: neither fcntl (POSIX) nor "
        f"msvcrt (Windows) is available on this platform -- refusing to "
        f"acquire fd {fd} unlocked (T-3506)"
    )


# frob:ticket T-3506
def _portable_flock_acquire_posix(
    fd: int, *, exclusive: bool, blocking: bool, timeout: float | None
) -> bool:
    """The `fcntl.flock` half of `portable_flock_acquire` -- split out
    (T-3506) purely to keep `portable_flock_acquire` itself under
    ARCH001's length/complexity threshold; assumes `fcntl is not None`
    (the caller already checked). See `portable_flock_acquire`'s own
    docstring for the three acquire-shape contract this implements."""
    assert fcntl is not None
    flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    if blocking and timeout is None:
        fcntl.flock(fd, flags)
        return True
    if not blocking:
        try:
            fcntl.flock(fd, flags | fcntl.LOCK_NB)
            return True
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            return False
    assert timeout is not None  # only remaining case: blocking, timed
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, flags | fcntl.LOCK_NB)
            return True
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)


# frob:ticket T-3506
def _portable_flock_acquire_windows(
    fd: int, *, blocking: bool, timeout: float | None
) -> bool:  # pragma: no cover -- windows-only
    """The `msvcrt.locking` half of `portable_flock_acquire` -- split out
    (T-3506) purely to keep `portable_flock_acquire` itself under
    ARCH001's length/complexity threshold; assumes `msvcrt is not None`
    (the caller already checked). See `portable_flock_acquire`'s own
    docstring for the three acquire-shape contract this implements.

    `msvcrt.locking` locks a byte RANGE, unlike `fcntl.flock`'s whole-
    descriptor lock -- it requires the target byte to already exist, so
    every msvcrt caller needs the file seeded with at least one byte
    first. Done HERE (T-3506) rather than at each call site: a caller
    that opens `fd` fresh (size 0) on POSIX never reaches this function
    at all, so seeding it only here -- never unconditionally at the call
    site -- is what keeps a POSIX caller's file layout byte-for-byte
    unchanged (T-3506's own must-stay-quiet bar) while still satisfying
    msvcrt's real precondition on Windows."""
    assert msvcrt is not None
    if os.fstat(fd).st_size < 1:
        os.write(fd, b"\0")
        os.fsync(fd)
    if blocking and timeout is None:
        _msvcrt_acquire_blocking(fd)
        return True
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            if not blocking:
                return False
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.05)


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_posix_blocking_acquire_release_round_trips  # noqa: E501
# frob:ticket T-3506
def portable_flock_release(fd: int) -> None:
    """Release a lock `portable_flock_acquire` took on `fd` -- the
    release half of the shared primitive, `fcntl.flock(fd, LOCK_UN)` on
    POSIX or `_msvcrt_release` on Windows. Raises `PortableLockUnavailable`
    in the same neither-backend case `portable_flock_acquire` does (never
    reached in practice: a caller that got a lock via `portable_flock_
    acquire` already proved a backend exists)."""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return
    if msvcrt is not None:  # pragma: no cover -- windows-only
        _msvcrt_release(fd)
        return
    raise PortableLockUnavailable(
        f"process: portable_flock_release: neither fcntl (POSIX) nor "
        f"msvcrt (Windows) is available on this platform -- cannot "
        f"release fd {fd} (T-3506)"
    )


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

# frob:ticket T-0918
# T-0918: PROCESS-wide (not thread-local) reentrancy signal. `_lock_local`
# above only answers "does THIS thread already hold the lock" -- it says
# nothing about a SIBLING thread in the same process (e.g. `frob check`'s
# `ThreadPoolExecutor` gate workers) holding it concurrently. `flock(2)`
# itself gives no same-process reentrancy across distinct open file
# descriptions: a worker thread that naively requested EXCLUSIVE while the
# main thread already holds SHARED on the same lock file would genuinely
# block against its own process's other thread -- a real deadlock, not a
# logical contract violation (see T-0879's Done report and this module's
# own docstring for the flock(2) citation). `_process_held_counts` tracks,
# per lock-file path, how many distinct real OS-level acquisitions (across
# ALL threads, ANY mode) are currently outstanding in THIS process; it is
# incremented exactly once per first-time (non-reentrant) acquire and
# decremented exactly once when that acquisition's final release happens,
# guarded by `_process_registry_lock` since multiple threads race on it
# concurrently. `derived_state_write_lock` below is the only reader.
_process_registry_lock = threading.Lock()
_process_held_counts: dict[str, int] = {}


#: T-0982: env var name a `ProcessPoolExecutor` OWNER stamps, before pool
#: construction, with the canonical registry keys (`_canonical_registry_key`
#: form, `os.pathsep`-joined) it currently holds `derived_state_lock` for in
#: THIS process. Mirrors `frob.gates._WORKER_STDOUT_LOG_LEVEL_ENV`'s (T-0806)
#: established pattern: env vars set on the parent's `os.environ` right
#: before constructing a `ProcessPoolExecutor` are inherited by every worker
#: it spawns (forkserver helper or spawn), so a worker's own
#: `derived_state_write_lock` call can see this marker even though
#: `_process_held_counts` itself is process-local and therefore invisible
#: across the fork/spawn boundary (the cross-process sibling of T-0918's
#: same-process registry).
# frob:ticket T-0982
_INHERITED_LOCK_KEYS_ENV = "FROB_DERIVED_LOCK_HELD_KEYS"

#: Separator `_INHERITED_LOCK_KEYS_ENV` joins multiple held keys with
#: (T-0982). `os.pathsep` (`:` on POSIX) rather than a comma: registry keys
#: are resolved filesystem paths, which never contain `os.pathsep` on a
#: POSIX host, whereas a path COULD legitimately contain a comma.
_INHERITED_LOCK_KEYS_SEP = os.pathsep


__all__ = [
    "derived_state_lock",
    "derived_state_write_lock",
    "held_registry_keys",
    "PortableLockUnavailable",
    "lock_backend_available",
    "portable_flock_acquire",
    "portable_flock_release",
]
