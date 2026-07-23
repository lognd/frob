"""Tests for `frob.process._lock.derived_state_lock` (T-0859): the
cross-process shared/exclusive `.frob/derived.lock` primitive `frob.check`'s
entry points hold for their entire run to close the cross-process TOCTOU
window T-0603's single in-process precheck left open."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from frob.process._lock import _derived_lock_path, derived_state_lock


# frob:ticket T-0859
class TestDerivedStateLock:
    """Exercises `derived_state_lock`'s file placement, re-entrancy, and
    real cross-thread shared/exclusive mutual-exclusion behavior."""

    # frob:ticket T-0859
    def test_lock_file_created_under_frob_dir(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_process_lock.py::TestDerivedStateLock.test_lock_file_created_under_frob_dir  # noqa: E501
        assert _derived_lock_path(tmp_path) == tmp_path / ".frob" / "derived.lock"
        with derived_state_lock(tmp_path, exclusive=False):
            pass
        assert _derived_lock_path(tmp_path).exists()

    # frob:ticket T-0859
    def test_reentrant_same_mode_in_same_thread(self, tmp_path: Path) -> None:
        """Nested `with derived_state_lock(..., exclusive=X)` requesting the
        SAME mode in the SAME thread must not deadlock."""
        with derived_state_lock(tmp_path, exclusive=False):
            with derived_state_lock(tmp_path, exclusive=False):
                pass
        with derived_state_lock(tmp_path, exclusive=True):
            with derived_state_lock(tmp_path, exclusive=True):
                pass

    # frob:ticket T-0859
    def test_reentrant_opposite_mode_raises(self, tmp_path: Path) -> None:
        """A same-thread re-entry requesting the OPPOSITE mode from the one
        already held is refused up front rather than silently deadlocking
        or silently violating the held mode."""
        with derived_state_lock(tmp_path, exclusive=False):
            try:
                with derived_state_lock(tmp_path, exclusive=True):
                    pass
            except RuntimeError as exc:
                assert "already held" in str(exc)
            else:
                raise AssertionError("expected RuntimeError on mode mismatch")

    # frob:ticket T-0859
    def test_two_threads_serialize_exclusive(self, tmp_path: Path) -> None:
        """Two threads racing for the EXCLUSIVE lock never overlap -- a
        real cross-thread mutual-exclusion check, not just "no exception"."""
        active = 0
        max_active = 0
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def worker() -> None:
            nonlocal active, max_active
            barrier.wait()
            with derived_state_lock(tmp_path, exclusive=True):
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.05)
                with lock:
                    active -= 1

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert max_active == 1

    # frob:ticket T-0859
    def test_shared_locks_do_not_block_each_other(self, tmp_path: Path) -> None:
        """Two SHARED holders can be inside the critical section at the
        same time -- the reader side of the reader/writer contract."""
        active = 0
        max_active = 0
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        def worker() -> None:
            nonlocal active, max_active
            barrier.wait()
            with derived_state_lock(tmp_path, exclusive=False):
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.1)
                with lock:
                    active -= 1

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert max_active == 2
