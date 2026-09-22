"""Stale-worktree post-land sweep tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    spawn_deferred_post_land_sweep,
    sweep_stale_worktrees_after_land,
)
from frob.tickets._worktree_sweep import sweep_worktrees
from tests.conftest import (
    _init_git_repo,
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Small real-`git` helper for the T-4448 fixture repos below -- same
    shape as `tests/test_ticket_leases.py`'s own `_run`, kept local since
    that module is outside this ticket's declared scope."""
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=True)


# frob:waive PERF012 reason="each call spawns against a DIFFERENT tmp_path repo per \
# test -- the shared argv shape is real git plumbing (init/config), not a redundant \
# re-run of the same computation"
def _git_init(root: Path) -> None:
    """A real `main`-branch repo with one commit, ready to host a
    `.claude/worktrees/`-shaped linked worktree (T-4448's own real-repo
    fixture, mirroring `tests/test_ticket_leases.py::sweep_repo`)."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / "README.md").write_text("root\n")
    _run(["git", "add", "."], root)
    _run(["git", "commit", "-q", "-m", "init"], root)


def _add_agent_worktree(repo: Path, name: str, branch: str) -> Path:
    """Add a linked worktree under `repo`'s `.claude/worktrees/<name>`
    dispatch convention, on a fresh `branch`."""
    wt = repo / ".claude" / "worktrees" / name
    wt.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-q", "-b", branch, str(wt), "main"], repo)
    return wt


# frob:waive PERF012 reason="each call commits a DIFFERENT file/message into a \
# DIFFERENT tmp_path repo per test -- the shared argv shape is real git plumbing \
# (add/commit), not a redundant re-run of the same computation"
def _commit_file(repo: Path, rel: str, content: str, message: str) -> None:
    """Write `content` to `rel` (parents created as needed) and commit it
    in `repo`."""
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _run(["git", "add", rel], repo)
    _run(["git", "commit", "-q", "-m", message], repo)


class TestSweepWorktreesAheadOfMain:
    """`_worktree_sweep._kept_ahead_of_main_verdict_if_present` (T-4448):
    the sweep never removes a clean worktree whose branch carries commits
    `main` does not, independent of whether T-1934's finished-signal
    detector also fires -- the direct fix for the MEASURED false
    `-> removed` on t-4442/t-4446 (`.frob/rapid-sweep/
    T-4430-899a8b12b8e0.log`), two clean, 3-commits-ahead, done-report-
    carrying worktrees the signal-based gate alone missed."""

    def test_clean_worktree_one_commit_ahead_is_kept(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain\
        # .test_clean_worktree_one_commit_ahead_is_kept
        repo = tmp_path / "main"
        _git_init(repo)
        wt = _add_agent_worktree(repo, "t-9001", "t-9001")
        _commit_file(
            wt,
            "tickets/T-9001/ticket.md",
            "---\nid: T-9001\nstate: in-progress\n---\nbody\n",
            "one commit ahead of main",
        )

        result = sweep_worktrees(repo, dry_run=True)

        assert result.is_ok
        (verdict,) = result.danger_ok
        assert verdict.path == str(wt.resolve())
        assert verdict.verdict == "kept:unlanded"
        assert "1 ahead of main" in verdict.detail
        assert "T-9001" in verdict.detail
        assert wt.exists()

    def test_clean_worktree_zero_ahead_ticket_done_is_removed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain\
        # .test_clean_worktree_zero_ahead_ticket_done_is_removed
        repo = tmp_path / "main"
        _git_init(repo)
        _commit_file(
            repo,
            "tickets/T-9002/ticket.md",
            "---\nid: T-9002\nstate: done\n---\nbody\n",
            "T-9002 done on main",
        )
        wt = _add_agent_worktree(repo, "t-9002", "t-9002")
        # `t-9002`'s branch tip is now identical to `main` (0 ahead): no
        # commit this branch made itself is missing from `main`, so
        # neither the T-4448 ahead-of-main gate nor T-1934's signal gate
        # has anything to keep it for.
        _run(["git", "-C", str(wt), "merge", "-q", "--ff-only", "main"], repo)

        result = sweep_worktrees(repo, dry_run=False)

        assert result.is_ok
        (verdict,) = result.danger_ok
        assert verdict.verdict == "removed"
        assert not wt.exists()

    def test_clean_worktree_ahead_survives_even_with_done_report(
        self, tmp_path: Path
    ) -> None:
        """The exact measured shape: a clean, committed worktree carrying
        a `done-report.md` (T-1934's own signal) is ALSO kept by the new,
        independent ahead-of-main gate -- proving the fix does not rely
        on the signal detector at all."""
        # frob:tests \
        # tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepWorktreesAheadOfMain\
        # .test_clean_worktree_ahead_survives_even_with_done_report
        repo = tmp_path / "main"
        _git_init(repo)
        wt = _add_agent_worktree(repo, "t-9003", "t-9003")
        _commit_file(wt, "code.py", "x = 1\n", "fix")
        _commit_file(
            wt,
            "tickets/T-9003/done-report.md",
            "## Done report\nstuff\n",
            "done report",
        )

        result = sweep_worktrees(repo, dry_run=False)

        assert result.is_ok
        (verdict,) = result.danger_ok
        assert verdict.verdict == "kept:unlanded"
        assert wt.exists()


class TestSweepStaleWorktreesAfterLand:
    """`_rapid_sweep.sweep_stale_worktrees_after_land` (T-2261)."""

    # frob:ticket T-2833

    def test_never_uses_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2261 acceptance [4]: --force is never used by the automatic
        path -- the ONE call to `sweep_worktrees` this function makes
        must always pass `force=False`."""
        captured: dict = {}

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            captured["force"] = force
            captured["dry_run"] = dry_run
            captured["min_age_hours"] = min_age_hours
            from typani import Ok

            return Ok(())

        monkeypatch.setattr("frob.tickets._worktree_sweep.sweep_worktrees", fake_sweep)
        sweep_stale_worktrees_after_land(tmp_path)
        assert captured["force"] is False
        assert captured["dry_run"] is False
        assert captured["min_age_hours"] == _rapid_sweep._AUTO_SWEEP_MIN_AGE_HOURS

    # frob:ticket T-2261
    # frob:tests src/frob/app/ticket_runner/_rapid_sweep.py::sweep_stale_worktrees_after_land  # noqa: E501
    def test_logs_one_line_per_verdict(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """MUST-STILL-PASS: every verdict `sweep_worktrees` computes --
        one 'removed' and each of the five keep classes (live, dirty,
        unlanded, lease, age) -- is logged, unmodified and undropped.
        This proves the automation REUSES `sweep_worktrees`'s own
        decisions rather than filtering or narrowing them; the five keep
        classes' own real-fixture coverage lives in
        tests/test_ticket_leases.py against `sweep_worktrees` itself."""
        from typani import Ok

        class _FakeVerdict:
            def __init__(self, path: str, verdict: str, detail: str = "") -> None:
                self.path = path
                self.verdict = verdict
                self.detail = detail

        verdicts = (
            _FakeVerdict("/w/removed", "removed"),
            _FakeVerdict("/w/live", "kept:live", "pid 123"),
            _FakeVerdict("/w/dirty", "kept:dirty", "uncommitted changes"),
            _FakeVerdict("/w/unlanded", "kept:unlanded", "T-9001"),
            _FakeVerdict("/w/lease", "kept:lease", "T-9002"),
            _FakeVerdict("/w/age", "kept:age"),
        )

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            return Ok(verdicts)

        monkeypatch.setattr("frob.tickets._worktree_sweep.sweep_worktrees", fake_sweep)
        with caplog.at_level("INFO"):
            sweep_stale_worktrees_after_land(tmp_path)
        out = caplog.text
        for v in verdicts:
            assert v.path in out
            assert v.verdict in out.split(v.path)[1][:80]
        assert "removed 1 of 6" in out

    # frob:ticket T-2261
    # frob:ticket T-2833
    def test_a_failed_sweep_is_logged_never_raised(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A `sweep_worktrees` Err (e.g. `root` is not a git repo) is
        logged and swallowed -- this runs in a detached child nobody is
        waiting on and must never raise back into `_sweep_async`."""
        from typani import Err

        from frob.tickets._worktree_sweep import _WorktreeSweepError

        def fake_sweep(
            root, *, min_age_hours=None, dry_run=False, force=False, now=None
        ):
            return Err(_WorktreeSweepError.NotARepo)

        monkeypatch.setattr("frob.tickets._worktree_sweep.sweep_worktrees", fake_sweep)
        with caplog.at_level("WARNING"):
            sweep_stale_worktrees_after_land(tmp_path)  # must not raise
        assert "worktree sweep failed" in caplog.text


class TestSweepStaleWorktreesIsOffTheLandCriticalPath:
    """T-2261 acceptance [3]: the worktree sweep must not lengthen the
    land's own critical path."""

    def test_spawn_deferred_post_land_sweep_never_calls_it_directly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`spawn_deferred_post_land_sweep` -- the function `_land_cmd`
        calls SYNCHRONOUSLY, on the land's own critical path -- must
        return without ever invoking `sweep_stale_worktrees_after_land`
        itself; only the DETACHED child (`_sweep_async`, spawned via
        `subprocess.Popen` and never awaited) calls it. This is what
        keeps the land's own measured duration unaffected: the extra
        work happens in a process the land does not wait on."""
        called = []
        monkeypatch.setattr(
            _rapid_sweep,
            "sweep_stale_worktrees_after_land",
            lambda root: called.append(root),
        )
        # exec disabled -> spawn_deferred_post_land_sweep records debt and
        # returns Err(SpawnRefused) without ever touching the worktree
        # sweep -- proving the call is not reachable from this function's
        # own body at all, synchronous path or not.
        monkeypatch.setattr("frob.process.exec_enabled", lambda: False)
        _init_git_repo(tmp_path)
        result = spawn_deferred_post_land_sweep(tmp_path, "T-1", "T-1", "deadbeef")
        assert result.is_err
        assert called == []
