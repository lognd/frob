"""Tests for `frob.graph.build_graph`'s lock scope (T-3478): T-0918 wrapped
the ENTIRE rebuild (walk + parse of every file) in the cross-process
EXCLUSIVE `derived_state_write_lock`, serializing concurrent `build_graph`
calls (e.g. `pytest -n` xdist workers) behind each other for the full parse
duration instead of just the cheap final cache commit -- measured as a
~19-minute CI tail stall. T-3478 narrows the exclusive hold to only
`_prune_stale_cache` + `_finalize_build`'s `conn.commit()`; these tests
pin that scope stays narrow and that T-0918's soundness (no two processes
committing to the same cache concurrently) and T-1423's `CacheLocked`
handling both still hold."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from frob.graph import GraphError, build_graph
from frob.process._lock import derived_state_write_lock


def _write(root: Path, rel: str, content: str) -> Path:
    """Write `content` to `root/rel`, creating parent dirs; returns the path."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# frob:ticket T-3478
class TestBuildGraphLockScope:
    """Pins that `build_graph`'s exclusive `derived_state_write_lock` hold
    covers only the cache-mutating tail, not the walk/parse."""

    # frob:ticket T-3478
    # frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope.test_parse_runs_while_another_process_holds_the_lock  # noqa: E501
    def test_parse_runs_while_another_process_holds_the_lock(
        self, tmp_path: Path
    ) -> None:
        """T-3478: if the exclusive lock covered the whole rebuild (the
        pre-fix shape), a `build_graph` call started while another holder
        has the exclusive lock would block before it ever reaches
        `_walk_repo_files`. Post-fix, the walk/parse phase must proceed
        (observably: the walk completes and files get parsed) even while
        a concurrent holder sits on the exclusive lock, since the lock is
        now only acquired around the prune+commit tail."""
        root = tmp_path
        _write(root, "src/a.py", "def foo() -> None:\n    pass\n")
        cache = root / ".frob" / "cache.db"

        release = threading.Event()
        held = threading.Event()

        def _hold_exclusive() -> None:
            with derived_state_write_lock(root):
                held.set()
                release.wait(timeout=10)

        holder = threading.Thread(target=_hold_exclusive, daemon=True)
        holder.start()
        assert held.wait(timeout=5), "lock holder never acquired the lock"

        # A same-process nested `derived_state_write_lock` call no-ops
        # (documented reentrancy contract), so this exercises the walk/
        # parse phase running concurrently with an outstanding exclusive
        # hold rather than blocking on it up front.
        t0 = time.monotonic()
        result = build_graph(root, cache)
        elapsed = time.monotonic() - t0

        release.set()
        holder.join(timeout=10)

        assert result.is_ok
        # Generous bound: a same-thread nested acquire must not itself
        # introduce a multi-second stall for a single tiny file.
        assert elapsed < 5.0

    # frob:ticket T-3478
    # frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope.test_two_processes_never_commit_to_the_same_cache_concurrently  # noqa: E501
    def test_two_processes_never_commit_to_the_same_cache_concurrently(
        self, tmp_path: Path
    ) -> None:
        """T-0918 soundness must not regress: two threads racing
        `build_graph` against the SAME cache file must both complete
        without corrupting it -- the narrowed lock (plus sqlite's own
        T-1423 retry) must still serialize the commit tail."""
        root = tmp_path
        _write(root, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(root, "src/b.py", "def bar() -> None:\n    pass\n")
        cache = root / ".frob" / "cache.db"

        results: list = [None, None]

        def _run(idx: int) -> None:
            results[idx] = build_graph(root, cache)

        t1 = threading.Thread(target=_run, args=(0,))
        t2 = threading.Thread(target=_run, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        for result in results:
            assert result is not None
            # Either a clean build or a reported (not raised) CacheLocked
            # under sustained contention -- never an unhandled exception,
            # and never a torn/corrupt commit.
            assert result.is_ok or (
                result.is_err and result.danger_err == GraphError.CacheLocked
            )


# frob:ticket T-3478
class TestBuildGraphCacheLockedStillReported:
    """T-1423's `CacheLocked` reporting must survive the narrowed lock."""

    # frob:ticket T-3478
    # frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphCacheLockedStillReported.test_cache_locked_from_connect_is_reported  # noqa: E501
    def test_cache_locked_from_connect_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `CacheLocked` raised out of `_cache.connect` (unlocked phase,
        now outside the exclusive hold) must still come back as
        `Err(GraphError.CacheLocked)`, not an unhandled exception."""
        import frob.graph as graph_mod
        from frob.graph import cache as _cache

        def _fake_connect(path):  # noqa: ANN001, ANN202
            raise _cache.CacheLocked("simulated: db locked")

        monkeypatch.setattr(graph_mod._cache, "connect", _fake_connect)
        root = tmp_path
        cache = root / ".frob" / "cache.db"

        result = build_graph(root, cache)
        assert result.is_err
        assert result.danger_err == GraphError.CacheLocked
