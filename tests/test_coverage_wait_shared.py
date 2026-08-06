"""Tests for `frob.testing._coverage_wait`'s T-1095 cross-worktree
single-flight layer: a single-flight lock and content-addressed result
cache keyed by `tree_digest` (tracked source content hash) rather than by
worktree path, so two worktrees of the SAME clone with byte-for-byte
identical tracked source share one real coverage run instead of each
independently paying for its own -- while two worktrees whose content
DIFFERS never contend with (or leak a result to) each other at all.
"""


from __future__ import annotations

import threading
import time
from pathlib import Path

import frob.process._guard as _guard
from frob.graph import build_graph
from frob.testing._coverage_wait import (
    CoverageWaitOutcome,
    run_coverage_wait,
    shared_state_dir,
    tree_digest,
)


def _make_repo(tmp_path: Path, name: str) -> Path:
    """A minimal single-module repo `run_coverage_wait` can build a graph
    snapshot against -- mirrors `tests/test_app.py::_make_repo`'s shape."""
    root = tmp_path / name
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
    return root


def _two_real_worktrees(tmp_path: Path) -> tuple[Path, Path]:
    """Two ACTUAL `git worktree`s of the same clone, checked out to the
    same commit -- the real cross-worktree shape T-1095's acceptance
    criteria name, not a simulated stand-in. Both resolve to the identical
    `git rev-parse --git-common-dir`, which is exactly the property
    `shared_state_dir` depends on to share state between them."""
    import subprocess

    origin = tmp_path / "origin"
    pkg = origin / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=origin, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=origin, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=origin, check=True)
    subprocess.run(["git", "add", "-A"], cwd=origin, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=origin, check=True)

    wt1 = tmp_path / "wt1"
    wt2 = tmp_path / "wt2"
    subprocess.run(["git", "worktree", "add", str(wt1)], cwd=origin, check=True)
    subprocess.run(
        ["git", "worktree", "add", "-b", "wt2-branch", str(wt2)], cwd=origin, check=True
    )
    return wt1, wt2


class TestTreeDigest:
    def test_identical_hashes_produce_identical_digest(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestTreeDigest.test_identical_hashes_prod\
        # uce_identical_digest
        root1 = _make_repo(tmp_path, "repo1")
        root2 = _make_repo(tmp_path, "repo2")
        cache1 = root1 / ".frob" / "cache.db"
        cache2 = root2 / ".frob" / "cache.db"
        snap1 = build_graph(root1, cache1).danger_ok
        snap2 = build_graph(root2, cache2).danger_ok
        assert tree_digest(snap1) == tree_digest(snap2)

    def test_differing_hashes_produce_differing_digest(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestTreeDigest.test_differing_hashes_prod\
        # uce_differing_digest
        root1 = _make_repo(tmp_path, "repo1")
        root2 = _make_repo(tmp_path, "repo2")
        (root2 / "src" / "pkg" / "mod.py").write_text(
            "def fn():\n    return 2\n", encoding="utf-8"
        )
        cache1 = root1 / ".frob" / "cache.db"
        cache2 = root2 / ".frob" / "cache.db"
        snap1 = build_graph(root1, cache1).danger_ok
        snap2 = build_graph(root2, cache2).danger_ok
        assert tree_digest(snap1) != tree_digest(snap2)


class TestSharedStateDir:
    def test_two_worktrees_of_same_clone_share_one_dir(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestSharedStateDir.test_two_worktrees_of_\
        # same_clone_share_one_dir
        wt1, wt2 = _two_real_worktrees(tmp_path)
        assert shared_state_dir(wt1) == shared_state_dir(wt2)

    def test_no_git_falls_back_to_worktree_local(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestSharedStateDir.test_no_git_falls_back\
        # _to_worktree_local
        bare = tmp_path / "not_a_repo"
        bare.mkdir()
        assert shared_state_dir(bare) == bare / ".frob" / "frob-coverage-shared"


class TestCrossWorktreeSingleFlight:
    """T-1095 acceptance [0]/[1]: real two-worktree concurrency."""

    def test_identical_digest_worktrees_share_one_run(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight.test_identi\
        # cal_digest_worktrees_share_one_run
        wt1, wt2 = _two_real_worktrees(tmp_path)

        run_count = 0
        run_lock = threading.Lock()

        real_run = _guard.subprocess.run

        def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
            nonlocal run_count
            if list(cmd) != ["true"]:
                # Let git's own spawns (git_common_dir, etc.) through
                # untouched -- only the coverage command itself is faked.
                return real_run(cmd, *args, **kwargs)
            with run_lock:
                run_count += 1
            # Hold briefly so the second worktree's caller has a real
            # window to arrive while the first is still "running" --
            # proving the second one blocks/adopts rather than racing
            # its own independent subprocess.
            time.sleep(0.2)

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)

        results: list = []
        results_lock = threading.Lock()

        def _call(root: Path) -> None:
            outcome = run_coverage_wait(root, command=("true",))
            with results_lock:
                results.append(outcome)

        barrier = threading.Barrier(2)

        def _synced_call(root: Path) -> None:
            barrier.wait()
            _call(root)

        t1 = threading.Thread(target=_synced_call, args=(wt1,))
        t2 = threading.Thread(target=_synced_call, args=(wt2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert run_count == 1, "identical-digest worktrees must share ONE real run"
        assert len(results) == 2
        assert all(r.is_ok for r in results)
        outcomes: list[CoverageWaitOutcome] = [r.danger_ok for r in results]
        # Exactly one caller actually ran it; the other adopted the cached
        # result with ran=False.
        assert sorted(o.ran for o in outcomes) == [False, True]

    def test_differing_digest_worktrees_each_run_independently(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestCrossWorktreeSingleFlight.test_differ\
        # ing_digest_worktrees_each_run_independently
        wt1, wt2 = _two_real_worktrees(tmp_path)
        # Make wt2's tracked content genuinely differ so its digest diverges
        # from wt1's.
        (wt2 / "src" / "pkg" / "mod.py").write_text(
            "def fn():\n    return 2\n", encoding="utf-8"
        )

        run_count = 0
        run_lock = threading.Lock()

        real_run = _guard.subprocess.run

        def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
            nonlocal run_count
            if list(cmd) != ["true"]:
                return real_run(cmd, *args, **kwargs)
            with run_lock:
                run_count += 1
            time.sleep(0.1)

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)

        results: list = []
        results_lock = threading.Lock()

        def _call(root: Path) -> None:
            outcome = run_coverage_wait(root, command=("true",))
            with results_lock:
                results.append(outcome)

        barrier = threading.Barrier(2)

        def _synced_call(root: Path) -> None:
            barrier.wait()
            _call(root)

        t1 = threading.Thread(target=_synced_call, args=(wt1,))
        t2 = threading.Thread(target=_synced_call, args=(wt2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert run_count == 2, "differing-digest worktrees must never share a run"
        assert len(results) == 2
        assert all(r.is_ok for r in results)
        outcomes: list[CoverageWaitOutcome] = [r.danger_ok for r in results]
        assert all(o.ran for o in outcomes)


def _start_socket_daemon(root: Path, idle_timeout_s: float = 5.0) -> threading.Thread:
    """Start a real `run_socket_daemon` in a background thread and block
    until its socket file exists -- mirrors `tests/test_app_daemon_proxy.
    py`'s own `_start_daemon` helper (T-1126: extracted here rather than
    inlined per test method, which a bare `frob-arch` walk mis-paired as
    nested loops across this class's two test methods)."""
    from frob.serve import SocketDaemonConfig, run_socket_daemon
    from frob.serve._socketd import socket_path

    cfg = SocketDaemonConfig(root=root, idle_timeout_s=idle_timeout_s)
    thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not socket_path(root).exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert socket_path(root).exists()
    return thread


def _shutdown_socket_daemon(root: Path, thread: threading.Thread) -> None:
    """Force the idle-timeout daemon down promptly rather than waiting out
    its full `idle_timeout_s` at teardown -- mirrors `tests/test_app_
    daemon_proxy.py`'s own `_shutdown` helper."""
    from frob.serve._socketd import lock_path, socket_path

    deadline = time.monotonic() + 5
    while (
        lock_path(root).exists() and time.monotonic() < deadline and thread.is_alive()
    ):
        time.sleep(0.05)
        if not socket_path(root).exists():
            break
    thread.join(timeout=1)


class TestWorktreeLock:
    """T-1126: `run_coverage_wait`'s OUTER single-flight lock prefers the
    T-1097 daemon lease RPC when a daemon is reachable for `root`, falling
    back to the original `_coverage_lock` file lock otherwise -- a real
    daemon (not a mock), per this file's own `TestCrossWorktreeSingleFlight`
    precedent."""

    def test_uses_daemon_lease_when_daemon_up(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestWorktreeLock.test_uses_daemon_lease_w\
        # hen_daemon_up
        import frob.testing._coverage_wait as _cw

        # T-1379 made the daemon path opt-IN (FROB_DAEMON=1) rather than
        # opt-out -- a live daemon socket alone no longer implies
        # `_daemon_enabled()`, so this test (written under T-1126, before
        # T-1379 shipped) must set the opt-in flag itself to exercise the
        # lease path it names.
        monkeypatch.setenv("FROB_DAEMON", "1")

        root = _make_repo(tmp_path, "proj")
        (root / ".frob").mkdir()

        thread = _start_socket_daemon(root)

        file_lock_calls = []
        real_coverage_lock = _cw._coverage_lock

        def _spy_coverage_lock(r):  # noqa: ANN001, ANN202
            file_lock_calls.append(r)
            return real_coverage_lock(r)

        monkeypatch.setattr(_cw, "_coverage_lock", _spy_coverage_lock)

        real_run = _guard.subprocess.run

        def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
            if list(cmd) != ["true"]:
                return real_run(cmd, *args, **kwargs)

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)

        try:
            result = run_coverage_wait(root, command=("true",))
        finally:
            _shutdown_socket_daemon(root, thread)

        assert result.is_ok
        assert file_lock_calls == [], (
            "a reachable daemon must arbitrate via the lease RPC, "
            "never falling through to the file lock"
        )

    def test_falls_back_to_file_lock_when_no_daemon(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_coverage_wait_shared.py::TestWorktreeLock.test_falls_back_to_file_\
        # lock_when_no_daemon
        import frob.testing._coverage_wait as _cw

        root = _make_repo(tmp_path, "proj")
        (root / ".frob").mkdir()
        monkeypatch.setenv("FROB_NO_DAEMON", "1")

        file_lock_calls = []
        real_coverage_lock = _cw._coverage_lock

        def _spy_coverage_lock(r):  # noqa: ANN001, ANN202
            file_lock_calls.append(r)
            return real_coverage_lock(r)

        monkeypatch.setattr(_cw, "_coverage_lock", _spy_coverage_lock)

        real_run = _guard.subprocess.run

        def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
            if list(cmd) != ["true"]:
                return real_run(cmd, *args, **kwargs)

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)

        result = run_coverage_wait(root, command=("true",))

        assert result.is_ok
        assert file_lock_calls == [root], (
            "no daemon reachable (FROB_NO_DAEMON=1) must fall back to the "
            "file lock exactly as before T-1126"
        )
