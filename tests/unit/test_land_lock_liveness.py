"""T-2155: regression lock for `land.lock` liveness after a SIGKILLed
holder.

The 2026-08-11 incident this ticket investigates: a `frob ticket land`
process died holding `.frob/land.lock`, the file survived on disk with
the dead pid's metadata still inside it, and four concurrent lands waited
out their full budget and refused rather than proceeding -- 25 minutes of
blocked fleet throughput before a human confirmed the pid was gone (via
`/proc/<pid>` and an `/proc/*/fd` scan) and removed the file by hand.

Investigation for this ticket found that `_land_lock` (`frob.tickets.
_land`) and `refuse_if_land_in_progress`/`_land_flock_probe` (`frob.
tickets._leases`) already treat liveness as the OS's job, not a recorded
field: both gate on a real, non-blocking `fcntl.flock(fd, LOCK_EX |
LOCK_NB)` acquisition attempt, and the JSON pid/session/started_at
content is used only for a blocked caller's diagnostic log line and for
`frob doctor`'s `LiveLandProcess` report (`_probe_land_lock_pid_
liveness`) -- never to decide whether a NEW acquisition is allowed. A
`flock` is released by the kernel the instant its holder's last file
descriptor closes, `SIGKILL` included, so a dead holder's lock is
released before this repo's own code ever runs again; nothing here reads
the stale pid to decide "is this held" the way a naive age/pid-based
scheme would (this is the mechanism T-2122 pointed at as its own prior
art: a shared, OS-arbitrated primitive instead of a per-process recorded
field a reader must independently prove stale).

This module locks that behavior in with a REAL subprocess and a REAL
`SIGKILL` (`multiprocessing.get_context("fork")`, matching `test_ticket_
land.py::TestSigkillMidStaging`'s own precedent and rationale for why an
in-process monkeypatch cannot stand in for this: a fake concurrency
simulation that calls back into the same lock from inside the same
process cannot reproduce a real held-then-orphaned OS lock at all). Both
tests here are expected to PASS against current `main` -- they exist to
prove the mechanism already holds and to catch a future regression that
would reintroduce a pid/age-based liveness heuristic in place of the
`flock` itself, not to demonstrate a live bug."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from pathlib import Path

from frob.tickets._land import _land_lock
from frob.tickets._leases import refuse_if_land_in_progress


# frob:waive WIRE001 reason="multiprocessing.Process(target=...) reference, not a call \
# expression -- a test-only fork-context worker used by the two SIGKILL regression \
# tests below, in this same file; no production caller by design, mirrors \
# test_ticket_land.py's own _t0907_child_land precedent" permanent="true"
def _child_hold_lock(root: Path, ready_path: Path) -> None:
    """Acquire `root`'s land.lock, signal readiness, then sleep -- the
    target `multiprocessing.get_context("fork")` runs as a real, separate
    OS process so a `SIGKILL` delivered to its pid is a genuine, kernel-
    level process death, not an in-process simulation."""
    with _land_lock(root, ticket_id="T-9999"):
        ready_path.write_text("ready\n")
        time.sleep(30)


def _spawn_and_kill_holder(root: Path, tmp_path: Path) -> int:
    """Fork a child that acquires `root`'s land.lock, wait for it to
    confirm acquisition, then SIGKILL it and wait for the OS to reap it.
    Returns the killed child's pid (now confirmed dead) for the caller's
    own assertions."""
    ready_path = tmp_path / "ready.flag"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(target=_child_hold_lock, args=(root, ready_path))
    proc.start()
    deadline = time.monotonic() + 20
    while not ready_path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert ready_path.exists(), "child never reached the lock-held checkpoint"
    assert proc.pid is not None
    killed_pid = proc.pid
    os.kill(killed_pid, signal.SIGKILL)
    proc.join(timeout=15)
    assert not proc.is_alive()
    return killed_pid


# frob:ticket T-2155
# frob:tests \
# tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder.test_land_\
# lock_reclaims_promptly_after_sigkill
class TestLandLockSurvivesSigkilledHolder:
    """`_land_lock` (the actual `land()` critical section) must not stay
    blocked by a dead holder -- the kernel's own `flock` release, not any
    recorded pid, is what unblocks the next acquisition."""

    def test_land_lock_reclaims_promptly_after_sigkill(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder.te\
        # st_land_lock_reclaims_promptly_after_sigkill
        root = tmp_path / "root"
        root.mkdir()
        killed_pid = _spawn_and_kill_holder(root, tmp_path)

        # Confirm the kernel actually reaped the process (matches the
        # incident's own /proc-based confirmation, not just proc.is_alive()
        # -- a genuinely gone pid is what makes this a fair test of
        # liveness-via-flock rather than liveness-via-recorded-pid).
        assert not Path(f"/proc/{killed_pid}").exists()

        start = time.monotonic()
        with _land_lock(root, ticket_id="T-8888", timeout=15.0):
            elapsed = time.monotonic() - start
        # A dead holder's flock is released by the kernel immediately; a
        # correct implementation reclaims well under one second, nowhere
        # near the 1509s/25-minute stall the real incident measured. 5s
        # leaves generous margin for CI/contended-host scheduling noise
        # while still failing hard if a future change reintroduces any
        # pid/age-based wait before reclaiming.
        assert elapsed < 5.0, (
            f"land.lock took {elapsed:.2f}s to reclaim after its holder was "
            "SIGKILLed -- liveness must come from the OS flock, not a "
            "recorded pid/age heuristic"
        )


# frob:ticket T-2155
# frob:tests \
# tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHol\
# der.test_refuse_if_land_in_progress_clears_promptly_after_sigkill
class TestRefuseIfLandInProgressSurvivesSigkilledHolder:
    """`refuse_if_land_in_progress` (every OTHER ledger-writing verb's
    choke point) must reach the same `Ok(None)` verdict promptly once the
    real holder is dead, not wait out its own bounded budget."""

    def test_refuse_if_land_in_progress_clears_promptly_after_sigkill(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigk\
        # illedHolder.test_refuse_if_land_in_progress_clears_promptly_after_sigkill
        root = tmp_path / "root"
        root.mkdir()
        killed_pid = _spawn_and_kill_holder(root, tmp_path)
        assert not Path(f"/proc/{killed_pid}").exists()

        start = time.monotonic()
        result = refuse_if_land_in_progress(root, wait_timeout_s=15.0)
        elapsed = time.monotonic() - start

        assert result.is_ok, result.err
        assert elapsed < 5.0, (
            f"refuse_if_land_in_progress took {elapsed:.2f}s to clear a "
            "SIGKILLed holder -- it must observe the OS-released flock "
            "promptly, not wait out a bounded budget calibrated for a "
            "genuinely live land"
        )
