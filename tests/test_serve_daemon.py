"""Tests for `frob.serve._daemon` (T-0733): the background post-land
re-verify job and the rebase-bot conflict-warning job, plus the
`frob_daemon_status` MCP tool that reads their cached result.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.serve import _daemon, _warm
from frob.serve._tools import frob_daemon_status
from frob.tickets._leases import record_lease


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A `main`-branch checkout with one committed file -- the minimal
    repo `poll_post_land`/`poll_rebase_bot` need a resolvable `main` HEAD
    against."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    _write(main_repo, "src/pkg/a.py", '"""Module."""\n')
    _commit_all(main_repo, "init")
    return main_repo


@pytest.fixture(autouse=True)
# frob:waive DEAD001 reason="T-1024: pytest autouse fixture, invoked by the test runner for every test in this module without ever appearing as a name/call token anywhere -- the one DEAD001 false-positive class autouse fixtures fall into, same disposition as tests/test_dup_cross_lang.py's own autouse fixture waiver"  # noqa: E501
def _clean_daemon_status():
    """Every test starts and ends with a clean `_daemon._STATUS`/`_warm`
    cache -- these module-level dicts persist across tests in the same
    process otherwise, and `tmp_path` never repeats so stale entries are
    harmless but the caches should not leak assumptions between tests."""
    _daemon._STATUS.clear()
    yield
    _daemon._STATUS.clear()


class TestPollPostLand:
    def test_head_unchanged_is_noop(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollPostLand.test_head_unchanged_is_noop
        _warm._invalidate(repo)
        first = _daemon._poll_post_land(repo, run_tests=False)
        assert first is not None
        second = _daemon._poll_post_land(repo, run_tests=False)
        assert second is not None
        assert second.checked_at == first.checked_at
        assert second.head == first.head

    def test_head_moved_refreshes_verdict(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollPostLand.test_head_moved_refreshes_verdict
        _warm._invalidate(repo)
        first = _daemon._poll_post_land(repo, run_tests=False)
        assert first is not None

        _write(repo, "src/pkg/b.py", '"""Second module."""\n')
        _commit_all(repo, "second commit")

        second = _daemon._poll_post_land(repo, run_tests=False)
        assert second is not None
        assert second.head != first.head


# frob:ticket T-0782
class TestPollRebaseBot:
    def test_no_leases_is_no_warnings(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollRebaseBot.test_no_leases_is_no_warnings
        warnings = _daemon._poll_rebase_bot(repo)
        assert warnings == ()

    def test_conflicting_branch_warns(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollRebaseBot.test_conflicting_branch_warns
        wt = repo.parent / "wt-conflict"
        _run(["git", "worktree", "add", "-b", "feature-conflict", str(wt)], repo)
        record_lease(wt, "T-0900", scope=("src/pkg/a.py",))

        _write(wt, "src/pkg/a.py", '"""Module."""\nx = "from-branch"\n')
        _commit_all(wt, "branch edit")

        _write(repo, "src/pkg/a.py", '"""Module."""\nx = "from-main"\n')
        _commit_all(repo, "main edit")

        warnings = _daemon._poll_rebase_bot(repo)
        assert len(warnings) == 1
        assert warnings[0].ticket_id == "T-0900"
        assert warnings[0].branch == "feature-conflict"

        status = _daemon.daemon_status(repo)
        assert status.rebase_warnings == warnings

    def test_clean_branch_no_warning(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollRebaseBot.test_clean_branch_no_warning
        wt = repo.parent / "wt-clean"
        _run(["git", "worktree", "add", "-b", "feature-clean", str(wt)], repo)
        record_lease(wt, "T-0901", scope=("src/pkg/b.py",))

        _write(wt, "src/pkg/b.py", '"""New module."""\n')
        _commit_all(wt, "branch add")

        _write(repo, "src/pkg/a.py", '"""Module."""\n# main-only change\n')
        _commit_all(repo, "main edit")

        warnings = _daemon._poll_rebase_bot(repo)
        assert warnings == ()

    # frob:ticket T-0782
    def test_ttl_expired_lease_skipped_and_logged_once(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-0782: a lease whose worktree path is still LIVE (so
        `read_all_leases`'s path-existence check alone would not drop it)
        but whose `recorded_at` is long past `LEASE_TTL_SECONDS` -- the
        deferred T-0476 dead-agent-with-a-live-worktree case. The daemon
        must skip re-simulating it (never conflict-warn for it) and log
        the skip exactly once across repeated poll cycles."""
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollRebaseBot.test_ttl_expired_lease_skipped_\
        # and_logged_once
        import logging

        from frob.tickets._leases import _LeaseRecord, leases_dir

        wt = repo.parent / "wt-dead-agent"
        _run(["git", "worktree", "add", "-b", "feature-dead", str(wt)], repo)
        # A conflicting branch edit, exactly like test_conflicting_branch_warns
        # -- if the daemon did NOT skip this lease, it would warn here.
        _write(wt, "src/pkg/a.py", '"""Module."""\nx = "from-dead-branch"\n')
        _commit_all(wt, "branch edit")
        _write(repo, "src/pkg/a.py", '"""Module."""\nx = "from-main"\n')
        _commit_all(repo, "main edit")

        resolved = leases_dir(repo)
        assert resolved.is_ok
        leases_root = resolved.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        stale = _LeaseRecord(
            ticket_id="T-0902",
            scope=("src/pkg/a.py",),
            worktree=str(wt.resolve()),
            branch="feature-dead",
            recorded_at="2000-01-01T00:00:00+00:00",
        )
        (leases_root / "T-0902.json").write_text(
            stale.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        caplog.set_level(logging.INFO, logger="frob.serve._daemon")

        first = _daemon._poll_rebase_bot(repo)
        second = _daemon._poll_rebase_bot(repo)

        assert first == ()
        assert second == ()

        skip_logs = [
            record
            for record in caplog.records
            if "T-0902" in record.getMessage() and "TTL" in record.getMessage()
        ]
        assert len(skip_logs) == 1


class TestPollRebaseBotLeaseInjectionGuard:
    """T-0780 (audit M1): a crafted lease written directly to the shared,
    peer-writable `frob-leases/` directory (bypassing `record_lease`
    entirely, simulating any co-located worktree agent's process) must
    never reach `poll_rebase_bot`'s `git merge-base`/`git merge-tree`
    argv -- `frob.tickets._leases.read_all_leases`'s admission check
    (T-0780) rejects it before `_worktree_branches` can ever hand it to
    `_merge_would_conflict`."""

    def test_evil_lease_branch_never_reaches_git_argv(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard.test_evil_le\
        # ase_branch_never_reaches_git_argv
        import logging

        from frob.tickets._leases import _LeaseRecord, leases_dir

        wt = repo.parent / "wt-evil"
        resolved = leases_dir(repo)
        assert resolved.is_ok
        leases_root = resolved.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        evil = _LeaseRecord(
            ticket_id="T-0666",
            scope=("src/pkg/a.py",),
            worktree=str(wt),
            branch="--output=/tmp/x",
            recorded_at="2026-07-23T00:00:00+00:00",
        )
        (leases_root / "T-0666.json").write_text(
            evil.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        calls: list[tuple[str, ...]] = []
        real_run_argv = _daemon.run_argv

        def _spy(argv):
            calls.append(tuple(argv))
            return real_run_argv(argv)

        monkeypatch.setattr(_daemon, "run_argv", _spy)
        caplog.set_level(logging.WARNING, logger="frob.tickets._leases")

        warnings = _daemon._poll_rebase_bot(repo)

        assert warnings == ()
        for argv in calls:
            assert "--output=/tmp/x" not in argv
        assert any(
            "T-0666" in record.getMessage() and "rejected lease" in record.getMessage()
            for record in caplog.records
        )


class TestRunDaemonCycle:
    def test_runs_both_jobs_and_returns_status(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestRunDaemonCycle.test_runs_both_jobs_and_return\
        # s_status
        _warm._invalidate(repo)
        status = _daemon._run_daemon_cycle(repo, run_tests=False)
        assert status.post_land is not None
        assert status.rebase_warnings == ()
        assert status.last_poll_at


class TestStartDaemon:
    def test_background_loop_runs_a_cycle_then_stops(
        self, repo: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestStartDaemon.test_background_loop_runs_a_cycle\
        # _then_stops
        import threading

        _warm._invalidate(repo)
        ran = threading.Event()
        real_cycle = _daemon._run_daemon_cycle

        def _spy(root: Path, *, run_tests: bool = True):
            result = real_cycle(root, run_tests=run_tests)
            ran.set()
            return result

        monkeypatch.setattr(_daemon, "_run_daemon_cycle", _spy)

        stop = _daemon._start_daemon(repo, interval_s=0.05, run_tests=False)
        try:
            # Generous timeout (a fast local cycle takes well under a
            # second): under heavy parallel test-suite load (many xdist
            # workers spawning git subprocesses concurrently) a tight
            # bound has been observed to flake even though the daemon
            # loop itself is correct -- this asserts the loop eventually
            # ran, not that it ran within one interval.
            assert ran.wait(timeout=30.0)
        finally:
            stop.set()


class TestFrobDaemonStatus:
    def test_reads_current_status(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_serve_daemon.py::TestFrobDaemonStatus.test_reads_current_status
        _warm._invalidate(repo)
        _daemon._poll_post_land(repo, run_tests=False)

        result = frob_daemon_status(repo)
        assert result.is_ok
        payload = result.danger_ok
        assert payload["post_land"] is not None
        assert payload["post_land"]["head"]
        assert payload["rebase_warnings"] == []
        assert payload["last_poll_at"]
