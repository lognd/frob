"""T-1358: regression tests for the release-quartet coherence guard added
to `frob.tickets._land_release._apply_release_bump` -- the incident class
where `_apply_release_bump`'s existing `_resync_release_manifest` step
(scoped to the `bumped.danger_ok is not None` branch) let a
`bump_version` callback report `Ok(None)` while `pyproject.toml`'s
on-disk version had already diverged from `.frob-release.json`'s, blocking
every subsequent land on the T-0992 monotonicity guard (the real T-1340
incident: pyproject.toml bumped 0.289.0 -> 0.290.0, `.frob-release.json`
left at 0.289.0)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from typani.result import Ok

from frob.tickets import _land_release
from frob.tickets._land_release import (
    _apply_release_bump,
    _ensure_release_quartet_coherent,
    _read_working_manifest_version,
    _read_working_pyproject_version,
)

if TYPE_CHECKING:
    from frob.tickets._models import Ticket


def _fake_run_argv(argv: list[str], **_kwargs: object):  # noqa: ANN201
    """Stand-in for `frob.gitio.run_argv` (T-1358): every git-mutating call
    `_apply_release_bump`'s own staging steps make (`git add`, and `uv
    lock` via `_sync_uv_lock_for_land`) reports success without touching a
    real repo -- these tests exercise the pure version-coherence logic, not
    git plumbing, which is already covered by `tests/test_ticket_land.py`'s
    real end-to-end fixtures."""
    return Ok(SimpleNamespace(returncode=0, stdout="", stderr=""))


@pytest.fixture(autouse=True)
def _no_real_subprocesses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this module runs against a bare `tmp_path`, not a git
    repo -- route `_land_release`'s own `run_argv` through `_fake_run_argv`
    so `git add`/`uv lock` staging calls succeed as no-ops instead of
    failing against a non-repo directory."""
    monkeypatch.setattr(_land_release, "run_argv", _fake_run_argv)


class _FakeTicket:
    """Minimal stand-in for `frob.tickets._models.Ticket` -- only the
    attributes `_apply_release_bump`'s callback contract touches."""

    title = "Do the thing"


def _fake_ticket() -> Ticket:
    """`_FakeTicket` typed as the `Ticket` the callee's signature declares.

    The stand-in is deliberately structural, so the cast is the honest
    way to say "only the callback contract's attributes are touched"
    without dragging a full `Ticket` construction into these tests."""
    return cast("Ticket", _FakeTicket())


def _write_pyproject(root: Path, version: str) -> None:
    """Write a minimal `pyproject.toml` at `version` for a test root."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8"
    )


def _write_manifest(root: Path, version: str) -> None:
    """Write a minimal `.frob-release.json` at `version` for a test root."""
    (root / ".frob-release.json").write_text(
        json.dumps({"version": version, "api": {}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class TestReadWorkingVersions:
    """`_read_working_pyproject_version`/`_read_working_manifest_version`
    read straight off the working tree, never a git object."""

    def test_reads_pyproject_version_from_disk(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestReadWorkingVersions.test_reads_pyproject_version_from_disk  # noqa: E501
        _write_pyproject(tmp_path, "1.2.3")
        assert _read_working_pyproject_version(tmp_path) == "1.2.3"

    def test_missing_pyproject_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestReadWorkingVersions.test_missing_pyproject_is_none  # noqa: E501
        assert _read_working_pyproject_version(tmp_path) is None

    def test_reads_manifest_version_from_disk(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestReadWorkingVersions.test_reads_manifest_version_from_disk  # noqa: E501
        _write_manifest(tmp_path, "1.2.3")
        assert _read_working_manifest_version(tmp_path) == "1.2.3"

    def test_missing_manifest_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestReadWorkingVersions.test_missing_manifest_is_none  # noqa: E501
        assert _read_working_manifest_version(tmp_path) is None

    def test_malformed_manifest_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestReadWorkingVersions.test_malformed_manifest_is_none  # noqa: E501
        (tmp_path / ".frob-release.json").write_text("not json", encoding="utf-8")
        assert _read_working_manifest_version(tmp_path) is None


class TestEnsureReleaseQuartetCoherent:
    """`_ensure_release_quartet_coherent` force-resyncs the manifest to
    pyproject.toml's on-disk version whenever the two disagree."""

    def test_already_coherent_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent.test_already_coherent_is_noop  # noqa: E501
        _write_pyproject(tmp_path, "0.290.0")
        _write_manifest(tmp_path, "0.290.0")

        result = _ensure_release_quartet_coherent(tmp_path, "T-1358")

        assert result.is_ok
        assert result.danger_ok is None
        assert _read_working_manifest_version(tmp_path) == "0.290.0"

    def test_diverged_versions_force_resync(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent.test_diverged_versions_force_resync  # noqa: E501
        # Reproduces the T-1340 incident directly: pyproject.toml already
        # bumped, .frob-release.json left behind at the old version.
        _write_pyproject(tmp_path, "0.290.0")
        _write_manifest(tmp_path, "0.289.0")

        result = _ensure_release_quartet_coherent(tmp_path, "T-1358")

        assert result.is_ok
        assert _read_working_manifest_version(tmp_path) == "0.290.0"

    def test_missing_manifest_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent.test_missing_manifest_is_noop  # noqa: E501
        _write_pyproject(tmp_path, "0.290.0")

        result = _ensure_release_quartet_coherent(tmp_path, "T-1358")

        assert result.is_ok
        assert result.danger_ok is None
        assert not (tmp_path / ".frob-release.json").exists()


class TestApplyReleaseBumpCoherenceGuard:
    """End-to-end through `_apply_release_bump`: a `bump_version` callback
    that writes pyproject.toml itself but reports `Ok(None)` (the T-1340
    incident's shape -- a bump happened on disk, but the branch that would
    normally force-resync the manifest never ran because it is gated on a
    non-None return value) must still leave the quartet coherent."""

    def test_callback_reports_none_but_pyproject_already_diverged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard.test_callback_reports_none_but_pyproject_already_diverged  # noqa: E501
        _write_pyproject(tmp_path, "0.289.0")
        _write_manifest(tmp_path, "0.289.0")

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            # Simulates a callback that bumps pyproject.toml on disk (as
            # T-1340's real land-time closure does) but, for whatever
            # reason, reports back that no bump happened.
            _write_pyproject(root, "0.290.0")
            return Ok(None)

        result = _apply_release_bump(
            tmp_path, _fake_ticket(), "T-1358", bump_version, pre_land_tip="HEAD"
        )

        assert result.is_ok
        assert _read_working_pyproject_version(tmp_path) == "0.290.0"
        assert _read_working_manifest_version(tmp_path) == "0.290.0"

    def test_callback_reports_new_version_normally(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard.test_callback_reports_new_version_normally  # noqa: E501
        _write_pyproject(tmp_path, "0.289.0")
        _write_manifest(tmp_path, "0.289.0")

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            _write_pyproject(root, "0.290.0")
            return Ok("0.290.0")

        result = _apply_release_bump(
            tmp_path, _fake_ticket(), "T-1358", bump_version, pre_land_tip="HEAD"
        )

        assert result.is_ok
        assert result.danger_ok == "0.290.0"
        assert _read_working_manifest_version(tmp_path) == "0.290.0"
