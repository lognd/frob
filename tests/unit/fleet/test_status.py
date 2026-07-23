"""Unit tests for frob.fleet.collect_status/rollup (docs/modules/fleet.md#collect,
docs/modules/fleet.md#rollup). git and `frob check` subprocess calls are
monkeypatched -- no real subprocess dependence, no network."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob import fleet as fleet_mod
from frob.fleet import (
    FleetManifest,
    GateSummary,
    RepoEntry,
    RepoStatus,
    collect_status,
    rollup,
)


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


_CHECK_JSON_PAYLOAD = (
    '{"path": ".", "results": ['
    '{"tool": "ruff-check", "exit_code": 1, '
    '"diagnostics": [{"severity": "error"}, {"severity": "warning"}]}, '
    '{"tool": "ty", "exit_code": 0, "diagnostics": []}'
    "]}"
)


# frob:ticket T-0803
class TestCollectStatus:
    def test_collect_status_ok(self, tmp_path: Path, monkeypatch) -> None:
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            if cmd[:2] == ["git", "status"]:
                return _FakeCompleted("# branch.head main\n1 .M N... file.py\n")
            if cmd[:2] == ["uv", "run"]:
                return _FakeCompleted(_CHECK_JSON_PAYLOAD)
            raise AssertionError(f"unexpected subprocess call: {cmd}")

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(
            fleet_mod,
            "_doable_count",
            lambda path: 3,  # noqa: ARG005
        )

        status = collect_status(RepoEntry(name="repo", path=repo_dir))
        assert status.name == "repo"
        assert status.branch == "main"
        assert status.dirty is True
        assert status.gates == GateSummary(error_count=1, warn_count=1, exit_code=0)
        assert status.doable_count == 3
        assert status.error is None

    def test_collect_status_probes_sibling_pinned_frob_not_bare_path_frob(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """CRITICAL regression (T-0573 review finding): the gate-summary
        probe must invoke the SIBLING's own pinned `frob` via `uv run
        --project <repo>`, never a bare `frob` resolved off this
        machine's PATH (a documented stale-global hazard, docs/guides/
        agent-playbook.md section 2) -- a bare-`frob` probe would look
        identical while silently reporting the wrong repo's gate
        counts."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            if cmd[:2] == ["git", "status"]:
                return _FakeCompleted("# branch.head main\n")
            captured.append(cmd)
            return _FakeCompleted(_CHECK_JSON_PAYLOAD)

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(fleet_mod, "_doable_count", lambda path: 0)  # noqa: ARG005

        collect_status(RepoEntry(name="repo", path=repo_dir))

        assert len(captured) == 1
        argv = captured[0]
        assert argv[0] != "frob", "must not invoke a bare frob off PATH"
        assert argv == [
            "uv",
            "run",
            "--project",
            str(repo_dir.resolve()),
            "frob",
            "check",
            "--json",
        ]

    def test_collect_status_missing_path(self, tmp_path: Path) -> None:
        status = collect_status(RepoEntry(name="ghost", path=tmp_path / "nope"))
        assert status.error is not None
        assert status.gates == GateSummary()
        assert status.doable_count == 0

    def test_git_branch_and_dirty_kill_switch_refuses_without_spawning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/fleet/test_status.py::TestCollectStatus.test_git_branch_and_dirty_kill_switch_refuses_without_spawning
        # T-0803: FROB_DISABLE_EXEC=1 must make `_git_branch_and_dirty`'s
        # `git status` spawn refuse (via `guarded_subprocess_run`) instead
        # of bypassing the T-0200/T-0778 exec guard -- proven with a spy on
        # the real `subprocess.run` so a spawn attempt would be observed.
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _spy)
        branch, dirty = fleet_mod._git_branch_and_dirty(tmp_path)
        assert not spawned
        assert branch is None
        assert dirty is False

    def test_gate_summary_probe_kill_switch_refuses_without_spawning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/fleet/test_status.py::TestCollectStatus.test_gate_summary_probe_kill_switch_refuses_without_spawning
        # T-0803: FROB_DISABLE_EXEC=1 must make `_gate_summary_probe`'s
        # `frob check --json` spawn refuse (via `guarded_subprocess_run`)
        # too -- proven with the same spy pattern.
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _spy)
        summary = fleet_mod._gate_summary_probe(tmp_path)
        assert not spawned
        assert summary == GateSummary()


class TestRollup:
    def test_rollup_orders_reddest_first(self, monkeypatch) -> None:
        clean = RepoStatus(name="clean", path=Path("."), gates=GateSummary())
        one_warn = RepoStatus(
            name="one-warn", path=Path("."), gates=GateSummary(warn_count=1)
        )
        two_errors = RepoStatus(
            name="two-errors", path=Path("."), gates=GateSummary(error_count=2)
        )

        by_name = {"clean": clean, "one-warn": one_warn, "two-errors": two_errors}

        def fake_collect(entry, *, probe_gates=True):  # noqa: ANN001, ARG001
            return by_name[entry.name]

        monkeypatch.setattr(fleet_mod, "collect_status", fake_collect)

        manifest = FleetManifest(
            repos=(
                RepoEntry(name="clean", path=Path(".")),
                RepoEntry(name="one-warn", path=Path(".")),
                RepoEntry(name="two-errors", path=Path(".")),
            )
        )
        report = rollup(manifest)
        assert [r.name for r in report.repos] == ["two-errors", "one-warn", "clean"]
