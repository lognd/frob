"""T-3088: `frob.tickets._land_compose` -- out-of-tree tree/commit-object
compose plus CAS ref publish, proven against a scratch git repo (never the
live root). Two properties matter: `compose_tree_out_of_tree` never touches
the checked-out working tree, and `publish_ref_cas` turns a lost race into
`Err(RefMoved)` rather than a silent overwrite or a corrupt ref."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets._land_compose import (
    LandComposeError,
    compose_tree_out_of_tree,
    publish_ref_cas,
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, asserting success -- test-only helper."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """A minimal git repo with one file committed on `main`, plus a
    `feature` branch that adds a second file -- the base fixture every
    test in this module composes against."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    (repo / "a.txt").write_text("base\n")
    _run(["git", "add", "a.txt"], repo)
    _run(["git", "commit", "-q", "-m", "base"], repo)

    _run(["git", "checkout", "-q", "-b", "feature"], repo)
    (repo / "b.txt").write_text("feature content\n")
    _run(["git", "add", "b.txt"], repo)
    _run(["git", "commit", "-q", "-m", "add b.txt"], repo)
    _run(["git", "checkout", "-q", "main"], repo)
    return repo


class TestComposeTreeOutOfTree:
    """`compose_tree_out_of_tree` builds a commit object without ever
    touching the checked-out working tree or HEAD."""

    def test_worktree_untouched_by_compose(self, scratch_repo: Path) -> None:
        """Given a scratch repo, when compose_tree_out_of_tree builds a
        commit, then the checked-out working tree is never touched
        (acceptance [0])."""
        a_path = scratch_repo / "a.txt"
        before_mtime = a_path.stat().st_mtime_ns
        before_listing = sorted(p.name for p in scratch_repo.iterdir() if p.name != ".git")

        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        result = compose_tree_out_of_tree(scratch_repo, base, feature)

        assert result.is_ok
        after_mtime = a_path.stat().st_mtime_ns
        after_listing = sorted(p.name for p in scratch_repo.iterdir() if p.name != ".git")
        assert after_mtime == before_mtime
        assert after_listing == before_listing
        # b.txt from the feature branch must NOT have materialized in the
        # working tree -- the compose is entirely out-of-tree.
        assert not (scratch_repo / "b.txt").exists()
        head = _run(["git", "symbolic-ref", "HEAD"], scratch_repo).stdout.strip()
        assert head == "refs/heads/main"

    def test_composed_commit_contains_the_patch(self, scratch_repo: Path) -> None:
        """The composed commit's tree really does contain the feature
        branch's change, proving this is a real compose and not a no-op."""
        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        result = compose_tree_out_of_tree(scratch_repo, base, feature)

        assert result.is_ok
        new_sha = result.danger_ok
        show = _run(["git", "show", f"{new_sha}:b.txt"], scratch_repo)
        assert show.stdout == "feature content\n"
        parent = _run(
            ["git", "rev-parse", f"{new_sha}^"], scratch_repo
        ).stdout.strip()
        assert parent == base

    def test_compose_failure_returns_err(self, scratch_repo: Path) -> None:
        """A base commit that does not exist fails cleanly with
        Err(ComposeFailed), never raising."""
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()
        result = compose_tree_out_of_tree(scratch_repo, "0" * 40, feature)
        assert result.is_err
        assert result.danger_err == LandComposeError.ComposeFailed


class TestPublishRefCas:
    """`publish_ref_cas` is `git update-ref <ref> <new> <old>` with a
    distinct RefMoved error on a lost race."""

    def test_sequential_publishes_succeed(self, scratch_repo: Path) -> None:
        """Must-stay-quiet fixture: sequential (non-racing) compose+publish
        pairs succeed every time."""
        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        composed = compose_tree_out_of_tree(scratch_repo, base, feature)
        assert composed.is_ok
        new_sha = composed.danger_ok

        published = publish_ref_cas(scratch_repo, "refs/heads/main", base, new_sha)
        assert published.is_ok
        tip = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        assert tip == new_sha

    def test_racing_publish_second_gets_ref_moved(self, scratch_repo: Path) -> None:
        """Given two racing publish_ref_cas calls with the same
        expected_old_sha, when the second runs after the first succeeds,
        then it returns Err(RefMoved) and the ref is not corrupted
        (acceptance [1])."""
        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        composed = compose_tree_out_of_tree(scratch_repo, base, feature)
        assert composed.is_ok
        winner_sha = composed.danger_ok

        # A second, independently composed candidate racing the SAME
        # expected_old_sha -- simulates a sibling land racing this one.
        (scratch_repo / "c.txt").write_text("other side\n")
        _run(["git", "add", "c.txt"], scratch_repo)
        _run(["git", "commit", "-q", "-m", "other side commit", "--allow-empty-message"], scratch_repo)
        other_branch_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()
        _run(["git", "reset", "-q", "--hard", base], scratch_repo)

        loser = compose_tree_out_of_tree(scratch_repo, base, other_branch_tip)
        assert loser.is_ok
        loser_sha = loser.danger_ok

        first = publish_ref_cas(scratch_repo, "refs/heads/main", base, winner_sha)
        assert first.is_ok

        second = publish_ref_cas(scratch_repo, "refs/heads/main", base, loser_sha)
        assert second.is_err
        assert second.danger_err == LandComposeError.RefMoved

        # The ref must still point at the WINNER's commit -- not corrupted,
        # not silently overwritten by the loser.
        tip = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        assert tip == winner_sha
