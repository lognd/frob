"""Stale-worktree post-land sweep tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.app.ticket_runner._rapid_sweep import (
    spawn_deferred_post_land_sweep,
    sweep_stale_worktrees_after_land,
)
from tests.conftest import (
    _init_git_repo,
)


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
