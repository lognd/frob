"""T-0338: unit tests for `frob.app.ticket_runner`'s land-time REL001
version-bump and native-rebuild-trigger helpers, exercised directly (no
real git worktree/subprocess needed for these pure/monkeypatched pieces --
the real end-to-end path is covered by tests/test_ticket_land.py's
`TestReleaseBump`/`TestRebuildNatives` against the library's injected
callables)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.app import ticket_runner
from frob.release import BumpClass, ReleaseManifest
from frob.tickets._models import LandError


class _FakeTicket:
    title = "Do the thing"


def _write_repo_files(root: Path, *, version: str = "0.1.0") -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n'
    )
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - unreleased\n")


class TestWriteReleaseBump:
    def test_rewrites_version_and_prepends_changelog_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump.test_rewrites_version_and_prepends_changelog_entry  # noqa: E501
        _write_repo_files(tmp_path)

        result = ticket_runner._write_release_bump(
            tmp_path, _FakeTicket(), "T-0001", "0.2.0"
        )
        assert result.is_ok

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert 'version = "0.2.0"' in pyproject
        assert 'version = "0.1.0"' not in pyproject

        changelog = (tmp_path / "CHANGELOG.md").read_text()
        assert "## [0.2.0] - unreleased" in changelog
        assert "T-0001: Do the thing" in changelog
        # The old entry must survive underneath the new one, unmodified.
        assert "## [0.1.0] - unreleased" in changelog

    def test_missing_version_line_fails(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump.test_missing_version_line_fails  # noqa: E501
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")

        result = ticket_runner._write_release_bump(
            tmp_path, _FakeTicket(), "T-0001", "0.2.0"
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed


class TestApplyReleaseBumpForLand:
    def test_no_manifest_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_no_manifest_is_noop  # noqa: E501
        _write_repo_files(tmp_path)
        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_bump_class_none_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_bump_class_none_is_noop  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        monkeypatch.setattr("frob.release.load_manifest", lambda root: Ok(manifest))
        monkeypatch.setattr(
            "frob.release.diff_class", lambda manifest, snapshot: BumpClass.NONE
        )
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Ok(object()))

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_bump_applies_writes_and_stamps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_bump_applies_writes_and_stamps  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        stamp_calls: list[str] = []
        monkeypatch.setattr("frob.release.load_manifest", lambda root: Ok(manifest))
        monkeypatch.setattr(
            "frob.release.diff_class", lambda manifest, snapshot: BumpClass.MINOR
        )
        monkeypatch.setattr(
            "frob.release.required_version",
            lambda previous, bump: Ok("0.2.0"),
        )

        def _fake_stamp(root: Path, snapshot: object, version: str):  # noqa: ANN202
            stamp_calls.append(version)
            (root / ".frob-release.json").write_text("{}")
            return Ok(version)

        monkeypatch.setattr("frob.release.stamp", _fake_stamp)
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Ok(object()))
        monkeypatch.setattr(
            "frob.gitio.run_argv",
            lambda argv, **kw: Ok(_FakeProc(0)),
        )

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok == "0.2.0"
        assert stamp_calls == ["0.2.0"]
        assert 'version = "0.2.0"' in (tmp_path / "pyproject.toml").read_text()

    def test_unreadable_graph_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_unreadable_graph_fails  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        monkeypatch.setattr("frob.release.load_manifest", lambda root: Ok(manifest))
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Err("boom"))

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestLandRebuildNativesFn:
    def test_success_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn.test_success_returns_true  # noqa: E501
        calls: list[list[str]] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            calls.append(argv)
            return _FakeProc(0)

        monkeypatch.setattr(ticket_runner.subprocess, "run", _fake_run)
        fn = ticket_runner._land_rebuild_natives_fn()
        assert fn(tmp_path) is True
        assert calls == [["make", "core"]]

    def test_failure_returns_false_and_logs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn.test_failure_returns_false_and_logs  # noqa: E501
        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stderr="boom")

        monkeypatch.setattr(ticket_runner.subprocess, "run", _fake_run)
        fn = ticket_runner._land_rebuild_natives_fn()
        with caplog.at_level("WARNING", logger="frob.app.ticket_runner"):
            assert fn(tmp_path) is False
        assert any("make core" in r.message for r in caplog.records)
