import os
import time

import frob.process._lock as _lock_mod


# frob:ticket T-3577
# frob:tests tests/unit/test_process_lock.py::TestPortableFlock.test_windows_blocking_reentry_raises_instead_of_hanging_forever  # noqa: E501
def _msvcrt_acquire_blocking(fd: int) -> None:  # pragma: no cover -- windows-only
    """Block (polling) until an exclusive `msvcrt.locking` byte-range
    lock on `fd`'s first byte is acquired -- `msvcrt` has no shared/read
    lock mode at all, so `derived_state_lock`'s Windows backend takes an
    EXCLUSIVE lock regardless of the caller's requested `exclusive`
    value (a documented, deliberate conservative-concurrency tradeoff:
    readers block each other too on Windows, which is safe, just less
    parallel than POSIX's real shared-lock semantics -- see that
    function's own docstring). Mirrors `frob.app.ticket_runner.
    _rapid_sweep`'s T-2918 `msvcrt.locking` retry-loop shape.

    T-3577: BOUNDED at `_MSVCRT_BLOCKING_ACQUIRE_CEILING_S`, unlike
    `fcntl.flock` without `LOCK_NB` (which blocks indefinitely on POSIX --
    safe there only because same-fd re-locking is a no-op). `msvcrt.
    locking` is not reentrant even on the same fd/process, so an unbounded
    version of this loop self-deadlocks FOREVER, with no external signal,
    the moment any caller nests a same-process re-acquire of a lock this
    backend already holds -- exactly the asymmetry that hung the
    windows-latest CI leg (T-3577's own measured root cause). Raises
    `PortableLockUnavailable` on expiry rather than returning False: this
    function's contract (mirroring bare `fcntl.flock(fd, LOCK_EX)`) is
    "always succeeds or raises", never a silent give-up a caller might
    mistake for "lock file missing" -- see `portable_flock_acquire`'s own
    `blocking=True, timeout=None` shape.

    T-3628: reads `_lock_mod.msvcrt`/`_lock_mod._MSVCRT_BLOCKING_ACQUIRE_CEILING_S`
    through the MODULE object rather than a plain `from frob.process._lock
    import ...` name-bind -- the latter freezes its own local copy at
    import time, invisible to the test suite's `monkeypatch.setattr(
    _lock_mod, "msvcrt"/"_MSVCRT_BLOCKING_ACQUIRE_CEILING_S", ...)` (it
    patches `frob.process._lock`'s attribute, not this module's)."""
    assert _lock_mod.msvcrt is not None
    deadline = time.monotonic() + _lock_mod._MSVCRT_BLOCKING_ACQUIRE_CEILING_S
    while True:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            _lock_mod.msvcrt.locking(fd, _lock_mod.msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise _lock_mod.PortableLockUnavailable(
                    f"process: _msvcrt_acquire_blocking: fd {fd} still "
                    f"locked after {_lock_mod._MSVCRT_BLOCKING_ACQUIRE_CEILING_S:g}s "
                    "(T-3577: msvcrt.locking is not reentrant -- this is "
                    "either genuine long-held cross-process contention, or "
                    "a same-process nested re-acquire that will never "
                    "resolve on its own)"
                ) from exc
            time.sleep(0.05)


def _msvcrt_release(fd: int) -> None:  # pragma: no cover -- windows-only
    """Release the byte-range lock `_msvcrt_acquire_blocking` took.

    T-3628: see `_msvcrt_acquire_blocking`'s docstring for why this reads
    `_lock_mod.msvcrt` through the module object."""
    assert _lock_mod.msvcrt is not None
    os.lseek(fd, 0, os.SEEK_SET)
    _lock_mod.msvcrt.locking(fd, _lock_mod.msvcrt.LK_UNLCK, 1)
