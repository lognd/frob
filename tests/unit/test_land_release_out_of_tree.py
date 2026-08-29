"""T-3095: `frob.tickets._land_release._apply_release_bump_out_of_tree` --
the release-bump treatment chosen for the "isolate land's post-squash
file-mutating stages" problem: run the existing `_apply_release_bump`
machinery against a disposable `git worktree`, never the caller's own
checked-out repo, so a concurrent `git status --porcelain` against the
repo sees nothing while the bump runs."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.tickets._land_release import _apply_release_bump_out_of_tree
from frob.tickets._models import LandError, Ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, asserting success -- test-only helper."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


class _FakeTicket:
    """Minimal stand-in for `Ticket` -- only what a `bump_version`
    callback's contract touches."""

    title = "Do the thing"


def _fake_ticket() -> Ticket:
    from typing import cast

    return cast("Ticket", _FakeTicket())


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """A minimal real git repo with `pyproject.toml` committed at
    0.1.0 -- the base fixture every test in this module composes
    against. A real repo (not a fake) is required: `_apply_release_bump_
    out_of_tree` proves its isolation property by actually creating a
    `git worktree` and observing `scratch_repo`'s own working tree/index
    around that call."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "release-bump-fixture"\nversion = "0.1.0"\n'
    )
    _run(["git", "add", "pyproject.toml"], repo)
    _run(["git", "commit", "-q", "-m", "base @ 0.1.0"], repo)
    return repo


def _composed_commit_with_extra_file(repo: Path) -> str:
    """Build a second commit on `main` (standing in for a real land's
    already-composed squash commit) that adds `feature.txt` -- the
    `composed_commit` these tests pass to `_apply_release_bump_out_of_
    tree`."""
    (repo / "feature.txt").write_text("landed content\n")
    _run(["git", "add", "feature.txt"], repo)
    _run(["git", "commit", "-q", "-m", "feature"], repo)
    return _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


class TestApplyReleaseBumpOutOfTree:
    """`_apply_release_bump_out_of_tree` runs the release bump against a
    disposable worktree and folds the result into a new commit, without
    ever touching `repo`'s own checked-out files."""

    def test_worktree_untouched_by_out_of_tree_bump(self, scratch_repo: Path) -> None:
        """Given a real repo, when the out-of-tree bump runs a
        `bump_version` callback that writes pyproject.toml, then
        `scratch_repo`'s OWN checked-out pyproject.toml is never touched
        (acceptance: the shared tree stays invisible during the bump)."""
        composed = _composed_commit_with_extra_file(scratch_repo)
        pre_land_tip = _run(["git", "rev-parse", "main~1"], scratch_repo).stdout.strip()
        before_text = (scratch_repo / "pyproject.toml").read_text()
        before_mtime = (scratch_repo / "pyproject.toml").stat().st_mtime_ns

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            (root / "pyproject.toml").write_text(
                '[project]\nname = "release-bump-fixture"\nversion = "0.2.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.2.0")

        result = _apply_release_bump_out_of_tree(
            scratch_repo, _fake_ticket(), "T-3095", bump_version, pre_land_tip, composed
        )

        assert result.is_ok, result.err
        assert (scratch_repo / "pyproject.toml").read_text() == before_text
        assert (scratch_repo / "pyproject.toml").stat().st_mtime_ns == before_mtime
        status = _run(["git", "status", "--porcelain"], scratch_repo).stdout
        assert status == ""

    def test_bump_folds_into_a_new_commit_on_composed_commit(
        self, scratch_repo: Path
    ) -> None:
        """A real bump's content shows up in the RETURNED commit, and
        `composed_commit`'s own changes (feature.txt) are still present --
        proving this is a real additive fold, not a no-op. The new commit
        is parented on `pre_land_tip`, not `composed_commit`, matching
        the real squash-apply's own single-parent commit shape (see this
        function's docstring for why)."""
        composed = _composed_commit_with_extra_file(scratch_repo)
        pre_land_tip = _run(["git", "rev-parse", "main~1"], scratch_repo).stdout.strip()

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            (root / "pyproject.toml").write_text(
                '[project]\nname = "release-bump-fixture"\nversion = "0.2.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.2.0")

        result = _apply_release_bump_out_of_tree(
            scratch_repo, _fake_ticket(), "T-3095", bump_version, pre_land_tip, composed
        )

        assert result.is_ok, result.err
        new_sha = result.danger_ok
        assert new_sha != composed
        show = _run(["git", "show", f"{new_sha}:pyproject.toml"], scratch_repo)
        assert "0.2.0" in show.stdout
        # feature.txt from the composed commit must still be present --
        # the fold is additive, not a fresh tree from pre_land_tip.
        feature = _run(["git", "show", f"{new_sha}:feature.txt"], scratch_repo)
        assert feature.stdout == "landed content\n"
        parent = _run(["git", "rev-parse", f"{new_sha}^"], scratch_repo).stdout.strip()
        assert parent == pre_land_tip

    def test_no_bump_returns_composed_commit_unchanged(
        self, scratch_repo: Path
    ) -> None:
        """`bump_version=None` (the no-op default) must return
        `composed_commit` itself, unchanged -- no new commit created for
        nothing to fold."""
        composed = _composed_commit_with_extra_file(scratch_repo)
        pre_land_tip = _run(["git", "rev-parse", "main~1"], scratch_repo).stdout.strip()

        result = _apply_release_bump_out_of_tree(
            scratch_repo, _fake_ticket(), "T-3095", None, pre_land_tip, composed
        )

        assert result.is_ok, result.err
        assert result.danger_ok == composed

    def test_bump_failure_leaves_repo_working_tree_untouched(
        self, scratch_repo: Path
    ) -> None:
        """A `bump_version` callback that reports `Err` propagates as
        `Err`, and `scratch_repo`'s own working tree/index stays clean --
        the failure path is just as isolated as the success path."""
        composed = _composed_commit_with_extra_file(scratch_repo)
        pre_land_tip = _run(["git", "rev-parse", "main~1"], scratch_repo).stdout.strip()

        def bump_version(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
            return Err(LandError.ReleaseBumpFailed)

        result = _apply_release_bump_out_of_tree(
            scratch_repo, _fake_ticket(), "T-3095", bump_version, pre_land_tip, composed
        )

        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        status = _run(["git", "status", "--porcelain"], scratch_repo).stdout
        assert status == ""
