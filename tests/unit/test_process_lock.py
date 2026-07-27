"""Tests for `frob.process._lock.derived_state_lock` (T-0859): the
cross-process shared/exclusive `.frob/derived.lock` primitive `frob.check`'s
entry points hold for their entire run to close the cross-process TOCTOU
window T-0603's single in-process precheck left open.

Also covers `derived_state_write_lock` (T-0918): the process-wide
reentrancy-aware writer entry point `frob.dup.find_clones`/
`frob.graph.build_graph` use, which must take a real exclusive lock
standalone but must not deadlock when nested inside a same-process SHARED
holder (`frob check`'s gate-worker threads)."""

from __future__ import annotations

import multiprocessing
import multiprocessing.synchronize
import threading
import time
from pathlib import Path

from frob.process._lock import (
    _derived_lock_path,
    _process_already_holds,
    derived_state_lock,
    derived_state_write_lock,
)


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


# frob:ticket T-0918
def _hold_exclusive_then_signal(
    root_str: str,
    ready: "multiprocessing.synchronize.Event",
    release: "multiprocessing.synchronize.Event",
) -> None:
    """Helper process (must be a top-level function to be picklable by
    `multiprocessing.Process`): takes a real EXCLUSIVE `derived_state_lock`
    in a SEPARATE process, signals `ready` once held, then blocks until the
    parent test signals `release` before letting go."""
    with derived_state_lock(Path(root_str), exclusive=True):
        ready.set()
        release.wait(timeout=10)


# frob:ticket T-0918
class TestDerivedStateWriteLock:
    """Exercises `derived_state_write_lock` (T-0918): the dup/graph cache
    rebuilders' entry point, which must take a real cross-process EXCLUSIVE
    lock when run standalone, but must NOT deadlock when nested inside a
    same-process SHARED holder (e.g. `frob check`'s gate-worker threads)."""

    # frob:ticket T-0918
    def test_standalone_rebuild_takes_exclusive(self, tmp_path: Path) -> None:
        """With NO outer holder anywhere in this process, `derived_state_
        write_lock` takes a real OS-level EXCLUSIVE `derived_state_lock`
        (visible via `_process_already_holds` flipping True for the
        duration and back to False on exit) -- the standalone-rebuild
        path, not a no-op. Real cross-process exclusivity for this same
        path is covered end-to-end by
        `test_concurrent_separate_process_writer_still_blocked` below."""
        assert not _process_already_holds(tmp_path)
        with derived_state_write_lock(tmp_path):
            assert _process_already_holds(tmp_path)
        assert not _process_already_holds(tmp_path)

    # frob:ticket T-0918
    def test_nested_inside_shared_holder_does_not_deadlock(
        self, tmp_path: Path
    ) -> None:
        """The check-style scenario T-0918 exists to fix: a main thread
        holds `derived_state_lock(..., exclusive=False)` for a whole run,
        and a DIFFERENT (gate-worker) thread calls `derived_state_write_lock`
        nested inside that. Must complete promptly (same-process no-op),
        not block forever waiting on the main thread's own held lock."""
        result: dict[str, bool] = {}

        def worker() -> None:
            with derived_state_write_lock(tmp_path):
                result["ran"] = True

        with derived_state_lock(tmp_path, exclusive=False):
            t = threading.Thread(target=worker)
            t.start()
            # Timeout guard: if this were a real deadlock, join() would
            # never return within the timeout and `t.is_alive()` would
            # still be True below -- fail loudly instead of hanging CI.
            t.join(timeout=5)
            assert not t.is_alive(), (
                "derived_state_write_lock deadlocked when nested inside a "
                "same-process SHARED holder (T-0918 regression)"
            )
        assert result.get("ran") is True

    # frob:ticket T-0918
    def test_concurrent_separate_process_writer_still_blocked(
        self, tmp_path: Path
    ) -> None:
        """A standalone `derived_state_write_lock` acquire in THIS process
        must still be blocked by a real EXCLUSIVE hold in a DIFFERENT OS
        process -- confirms the T-0918 same-process no-op path did not
        accidentally weaken the underlying cross-process guarantee
        `derived_state_lock` itself provides."""
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        release = ctx.Event()
        proc = ctx.Process(
            target=_hold_exclusive_then_signal,
            args=(str(tmp_path), ready, release),
        )
        proc.start()
        try:
            assert ready.wait(timeout=10), (
                "helper process never signaled it acquired the exclusive lock"
            )

            acquired_at: list[float] = []

            def acquire_in_parent() -> None:
                with derived_state_write_lock(tmp_path):
                    acquired_at.append(time.monotonic())

            t = threading.Thread(target=acquire_in_parent)
            start = time.monotonic()
            t.start()
            # Give the parent's acquire attempt a moment to genuinely
            # block against the other process's exclusive hold.
            t.join(timeout=0.3)
            assert t.is_alive(), (
                "parent-process derived_state_write_lock acquired the lock "
                "while a DIFFERENT process still held it exclusively -- "
                "cross-process exclusion regressed"
            )

            release.set()
            t.join(timeout=10)
            assert not t.is_alive()
            assert acquired_at and acquired_at[0] > start
        finally:
            release.set()
            proc.join(timeout=10)


# frob:ticket T-0933
class TestProcessRegistryCanonicalKey:
    """Regression coverage for T-0933: a T-0918 regression where `frob
    check`'s outer SHARED `derived_state_lock(root, ...)` and a nested
    `derived_state_write_lock(root)` call disagreed on the process-wide
    reentrancy registry key whenever the two call sites spelled the SAME
    on-disk `root` differently (e.g. one unresolved/relative, one via
    `root.resolve()`) -- `_process_already_holds` read `False` for the
    resolved spelling even though the unresolved spelling's SHARED hold
    was outstanding in this same process, so the nested writer attempted a
    real second `flock(LOCK_EX)` against its own process's `LOCK_SH` and
    self-deadlocked. Covers both directions: shared-then-nested-write and
    write-then-nested-shared-read, each with mismatched spellings."""

    # frob:tests tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey.test_shared_unresolved_then_nested_write_resolved_does_not_deadlock  # noqa: E501
    def test_shared_unresolved_then_nested_write_resolved_does_not_deadlock(
        self, tmp_path: Path
    ) -> None:
        """Outer SHARED hold uses an UNRESOLVED spelling of `root`
        (`tmp_path / "."`, matching how a relative/uncanonicalized root
        historically reached `frob.check`'s outer lock call); a nested
        `derived_state_write_lock` on the RESOLVED spelling (matching
        `frob.graph.build_graph`'s `root.resolve()`) must see the
        process-wide reentrancy signal and no-op instead of deadlocking."""
        unresolved_root = tmp_path / "." / "nested" / ".."
        resolved_root = tmp_path.resolve()
        result: dict[str, bool] = {}

        def worker() -> None:
            with derived_state_write_lock(resolved_root):
                result["ran"] = True

        with derived_state_lock(unresolved_root, exclusive=False):
            assert _process_already_holds(resolved_root), (
                "process-wide reentrancy signal did not recognize a "
                "differently-spelled but equivalent root as already held "
                "(T-0933 canonical-key regression)"
            )
            t = threading.Thread(target=worker)
            t.start()
            t.join(timeout=5)
            assert not t.is_alive(), (
                "derived_state_write_lock deadlocked against its own "
                "process's SHARED hold on a differently-spelled root "
                "(T-0933 regression)"
            )
        assert result.get("ran") is True

    # frob:tests tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey.test_write_resolved_then_nested_shared_unresolved_agrees  # noqa: E501
    def test_write_resolved_then_nested_shared_unresolved_agrees(
        self, tmp_path: Path
    ) -> None:
        """Reverse spelling direction: an outer EXCLUSIVE writer hold on
        the RESOLVED spelling must be visible to `_process_already_holds`
        queried with the UNRESOLVED spelling of the same root."""
        resolved_root = tmp_path.resolve()
        unresolved_root = tmp_path / "." / "nested" / ".."

        with derived_state_write_lock(resolved_root):
            assert _process_already_holds(unresolved_root), (
                "process-wide reentrancy signal did not recognize a "
                "differently-spelled but equivalent root as already held "
                "(T-0933 canonical-key regression, reverse direction)"
            )
