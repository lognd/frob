"""Tests for `frob test --wait-coverage` (T-0322): the foreground,
single-flight, blocking-until-fresh coverage contract that replaces
backgrounding `make coverage` and stalling on a notification a dispatched
sub-agent can never receive (docs/guides/agent-playbook.md section 6b)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app.config import AppConfig
from frob.app.test_runner import run
from frob.gates import stamp_coverage
from frob.graph import build_graph
from frob.testing import (
    CoverageWaitError,
    CoverageWaitOutcome,
    coverage_lock_path,
    run_coverage_wait,
)


def _make_repo(tmp_path: Path) -> Path:
    """A minimal single-module repo `run_coverage_wait` can build a graph
    snapshot against."""
    root = tmp_path / "repo"
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
    return root


# frob:ticket T-0803
class TestRunCoverageWait:
    def test_coverage_lock_path_is_under_frob_dir(self, tmp_path):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_coverage_lock_path_is_under_frob_dir  # noqa: E501
        assert coverage_lock_path(tmp_path) == tmp_path / ".frob" / "coverage.lock"

    # frob:ticket T-0803
    def test_no_stamp_runs_command_and_reports_ran(self, tmp_path, monkeypatch):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_no_stamp_runs_command_and_reports_ran  # noqa: E501
        root = _make_repo(tmp_path)
        calls: list[list[str]] = []

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            calls.append(list(cmd))

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("true",))
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.ran is True
        assert calls == [["true"]]

    # frob:ticket T-0803
    def test_fresh_stamp_skips_the_run(self, tmp_path, monkeypatch):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_fresh_stamp_skips_the_run  # noqa: E501
        root = _make_repo(tmp_path)
        cache = root / ".frob" / "cache.db"
        build_graph(root, cache).danger_ok
        (root / "coverage.xml").write_text("<coverage/>", encoding="utf-8")
        stamped = stamp_coverage(root)
        assert stamped.is_ok

        called = False

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            nonlocal called
            called = True

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("true",))
        assert result.is_ok
        assert result.danger_ok.ran is False
        assert called is False

    # frob:ticket T-0803
    def test_failed_command_is_err(self, tmp_path, monkeypatch):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_failed_command_is_err  # noqa: E501
        root = _make_repo(tmp_path)

        def _fake_run(cmd, cwd, check):  # noqa: ANN001
            class _Result:
                returncode = 1

            return _Result()

        monkeypatch.setattr("frob.process._guard.subprocess.run", _fake_run)
        result = run_coverage_wait(root, command=("false",))
        assert result.is_err
        assert result.danger_err == CoverageWaitError.RunFailed

    def test_kill_switch_refuses_without_spawning(self, tmp_path, monkeypatch):
        # frob:tests tests/test_app.py::TestRunCoverageWait.test_kill_switch_refuses_without_spawning  # noqa: E501
        # T-0803: FROB_DISABLE_EXEC=1 must make `run_coverage_wait`'s
        # coverage-suite spawn refuse (via `guarded_subprocess_run`)
        # instead of bypassing the T-0200/T-0778 exec guard -- proven with
        # a spy on the real `subprocess.run` so a spawn attempt would be
        # observed, not assumed.
        import subprocess

        root = _make_repo(tmp_path)
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr("frob.process._guard.subprocess.run", _spy)
        result = run_coverage_wait(root, command=("true",))
        assert not spawned
        assert result.is_err
        assert result.danger_err == CoverageWaitError.RunFailed


class TestWaitCoverage:
    """`frob test --wait-coverage` dispatch (test_runner.py::run)."""

    def test_wait_coverage_flag_dispatches_and_exits_zero_on_success(
        self, tmp_path, monkeypatch
    ) -> None:
        # frob:tests tests/test_app.py::TestWaitCoverage.test_wait_coverage_flag_dispatches_and_exits_zero_on_success  # noqa: E501
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        recorded: dict[str, object] = {}

        def _fake_wait(root):  # noqa: ANN001
            recorded["root"] = root
            return Ok(CoverageWaitOutcome(ran=True, duration_s=1.5))

        monkeypatch.setattr("frob.testing.run_coverage_wait", _fake_wait)
        cfg = AppConfig(
            test_wait_coverage=True,
            test_path=tmp_path,
        )
        run(cfg)  # must not raise/exit
        assert recorded["root"] == tmp_path.resolve()

    def test_wait_coverage_flag_exits_1_on_failure(self, tmp_path, monkeypatch) -> None:
        # frob:tests tests/test_app.py::TestWaitCoverage.test_wait_coverage_flag_exits_1_on_failure  # noqa: E501
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

        def _fake_wait(root):  # noqa: ANN001
            return Err(CoverageWaitError.RunFailed)

        monkeypatch.setattr("frob.testing.run_coverage_wait", _fake_wait)
        cfg = AppConfig(
            test_wait_coverage=True,
            test_path=tmp_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 1
