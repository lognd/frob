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
import subprocess
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
    _read_working_uv_lock_version,
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


# frob:ticket T-1771
class TestUvLockCoherenceWhenAlreadyBumped:
    """T-1771 item 1: the real shape a `bump_version` callback returning
    `Ok(None)` produces is pyproject.toml and `.frob-release.json`
    ALREADY agreeing (nothing for the manifest-resync branch to do) --
    `_ensure_uv_lock_coherent` must still run and fix a `uv.lock` that is
    a version behind, not be skipped because the manifest half found
    nothing to do. Asserts the lock's own RECORDED VERSION after the
    call, not merely that a sync helper was invoked."""

    def test_stale_lock_resynced_even_when_pyproject_and_manifest_agree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped.test_stale_lock_resynced_even_when_pyproject_and_manifest_agree  # noqa: E501
        _write_pyproject(tmp_path, "0.290.0")
        _write_manifest(tmp_path, "0.290.0")
        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.289.0"\n', encoding="utf-8"
        )

        def _fake_uv_lock_rewrite(argv, **_kwargs):  # noqa: ANN001, ANN201
            # A realistic-enough `uv lock` stand-in: actually rewrites the
            # on-disk lock's recorded version, so the test can assert
            # against the real artifact instead of a mock call count.
            if list(argv[:2]) == ["uv", "lock"]:
                (tmp_path / "uv.lock").write_text(
                    '[[package]]\nname = "frob"\nversion = "0.290.0"\n',
                    encoding="utf-8",
                )
            return Ok(SimpleNamespace(returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(_land_release, "run_argv", _fake_uv_lock_rewrite)

        result = _ensure_release_quartet_coherent(tmp_path, "T-1771")

        assert result.is_ok, result.danger_err
        assert _read_working_uv_lock_version(tmp_path) == "0.290.0"

    def test_lock_already_coherent_is_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped.test_lock_already_coherent_is_untouched  # noqa: E501
        _write_pyproject(tmp_path, "0.290.0")
        _write_manifest(tmp_path, "0.290.0")
        (tmp_path / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.290.0"\n', encoding="utf-8"
        )

        calls: list[list[str]] = []

        def _tracking_run_argv(argv, **_kwargs):  # noqa: ANN001, ANN201
            calls.append(list(argv))
            return Ok(SimpleNamespace(returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(_land_release, "run_argv", _tracking_run_argv)

        result = _ensure_release_quartet_coherent(tmp_path, "T-1771")

        assert result.is_ok
        assert not any(list(c[:2]) == ["uv", "lock"] for c in calls), (
            "an already-coherent lock must not trigger a re-sync spawn"
        )


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


def _git(root: Path, *args: str) -> None:
    """Run a real `git` command against `root`, failing the test loudly on
    any non-zero exit -- these T-1760 tests need real git history (a
    genuine 3-way squash-merge is the whole mechanism under test), not the
    `_fake_run_argv` stub the rest of this module uses."""
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"


class TestResetReleaseArtifactsRealGitRepo:
    """T-1760, against a REAL git repository (not the `_fake_run_argv`
    stub): whatever `git merge --squash` staged for `pyproject.toml`/
    `.frob-release.json` in `root`'s working tree/index BEFORE
    `_apply_release_bump` ever runs must not survive it -- the artifacts
    are RECOMPUTED from `pre_land_tip`, never CARRIED from whatever
    happened to already be staged (required item 3 of T-1760).

    Deliberately does not attempt to reproduce the EXACT git-diff3
    decision tree that let a real squash-merge land a regression cleanly
    (multiple candidate mechanisms exist -- an intermediate `git merge
    main` captured into a worktree's own history, a stale merge-base from
    a long-lived branch, or a genuine conflict whose resolution this
    investigation did not fully isolate) -- instead, it reproduces the
    STATE the defect produces (root's working tree/index already holding
    a version/manifest below `pre_land_tip`'s own committed value,
    established via a real `git add`, not a hand-built fixture object)
    and proves the fix is unconditional: regardless of HOW that state
    arose, `_apply_release_bump` must still leave `root` at `pre_land_tip`
    's value or later, never behind it. `tests/test_ticket_land.py` (T-1721
    precedent) is the home for a full-CLI, real-squash-merge reproduction;
    out of this ticket's own declared scope."""

    @pytest.fixture(autouse=True)
    def _real_git_ops(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Undo the module's `_fake_run_argv` autouse patch for this class
        only -- these tests need `_land_release.run_argv` to hit a real
        git subprocess, since the checkout/show plumbing under test IS
        the mechanism being verified."""
        from frob.gitio import run_argv as real_run_argv

        monkeypatch.setattr(_land_release, "run_argv", real_run_argv)

    def _init_repo(self, root: Path) -> None:
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "test@example.com")
        _git(root, "config", "user.name", "Test")

    def _commit_release_state(self, root: Path, version: str, *, message: str) -> str:
        """Write `pyproject.toml`/`.frob-release.json` at `version` and
        commit them, returning the new commit sha -- one rung of the
        T-1760 repro's commit ladder."""
        _write_pyproject(root, version)
        _write_manifest(root, version)
        _git(root, "add", "pyproject.toml", ".frob-release.json")
        _git(root, "commit", "-m", message)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def test_regressed_working_tree_is_reset_before_bump_runs(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo.test_regressed_working_tree_is_reset_before_bump_runs  # noqa: E501
        #
        # Reproduces the T-1760 field incident's STATE directly: main
        # (`pre_land_tip`) is committed at 0.366.0 (a sibling's already-
        # landed bump); the working tree/index -- as a squash-apply would
        # leave it -- already holds a REGRESSED 0.365.0 for both files,
        # staged via a real `git add`, before `_apply_release_bump` ever
        # runs. A `bump_version` callback reporting `Ok(None)` (this
        # land's own diff needs no new public-API bump -- the exact
        # branch that used to leave the regression uncorrected) must
        # still leave root at 0.366.0, not 0.365.0.
        self._init_repo(tmp_path)
        pre_land_tip = self._commit_release_state(
            tmp_path,
            "0.366.0",
            message="main @ 0.366.0 (a sibling's already-landed bump)",
        )

        # Simulate whatever the squash-apply left behind: a regressed,
        # internally-coherent pair, staged in the index exactly as
        # `git merge --squash` would leave it (uncommitted, but `git add`ed).
        _write_pyproject(tmp_path, "0.365.0")
        _write_manifest(tmp_path, "0.365.0")
        _git(tmp_path, "add", "pyproject.toml", ".frob-release.json")

        # Confirm the corrupted state is real before any fix runs.
        assert _read_working_pyproject_version(tmp_path) == "0.365.0"
        assert _read_working_manifest_version(tmp_path) == "0.365.0"

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            return Ok(None)

        result = _apply_release_bump(
            tmp_path, _fake_ticket(), "T-1760", bump_version, pre_land_tip=pre_land_tip
        )

        assert result.is_ok, result.err
        assert _read_working_pyproject_version(tmp_path) == "0.366.0"
        assert _read_working_manifest_version(tmp_path) == "0.366.0"

    def test_legitimate_bump_still_advances_past_the_reset_baseline(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo.test_legitimate_bump_still_advances_past_the_reset_baseline  # noqa: E501
        #
        # The reset must not fight a REAL bump this land itself needs --
        # after resetting to pre_land_tip's 0.366.0, a `bump_version`
        # callback that legitimately writes 0.367.0 must still land at
        # 0.367.0, not be clobbered back to 0.366.0.
        self._init_repo(tmp_path)
        pre_land_tip = self._commit_release_state(
            tmp_path, "0.366.0", message="base @ 0.366.0"
        )

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            _write_pyproject(root, "0.367.0")
            _write_manifest(root, "0.367.0")
            return Ok("0.367.0")

        result = _apply_release_bump(
            tmp_path, _fake_ticket(), "T-1760", bump_version, pre_land_tip=pre_land_tip
        )

        assert result.is_ok, result.err
        assert result.danger_ok == "0.367.0"
        assert _read_working_pyproject_version(tmp_path) == "0.367.0"
        assert _read_working_manifest_version(tmp_path) == "0.367.0"
