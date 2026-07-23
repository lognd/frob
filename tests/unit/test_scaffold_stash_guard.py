"""T-0870: the scaffolded stash-guard `reference-transaction` hook must
distinguish a genuine `git stash` ref-update (value changes) from a
maintenance rewrite of the same ref (`git gc` / `git pack-refs`, value
unchanged) -- only the former is refused in a multi-worktree clone.

All fixtures here are throwaway `tmp_path` git repos, never the real
clone's own hooks (docs/guides/agent-playbook.md#1b's own hook install
is out of scope to exercise directly)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.scaffold._managed import apply_managed_blocks


# frob:ticket T-0870
def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, never raising -- callers assert on the
    returncode/output themselves."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


# frob:ticket T-0870
def _init_repo(root: Path) -> None:
    """A minimal git repo at `root` with one commit, so `git worktree add`
    and `git stash` both have something to work against."""
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("hello\n")
    _git("add", "README.md", cwd=root)
    _git("commit", "-q", "-m", "initial", cwd=root)


# frob:ticket T-0870
class TestStashGuardPackRefs:
    """`git gc`/`git pack-refs` must succeed under the T-0574 stash-guard
    hook even with a pre-existing `refs/stash` and >1 worktree (T-0870);
    a genuine `git stash` must still be refused in the same clone."""

    # frob:ticket T-0870
    # frob:tests tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs.test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees  # noqa: E501
    def test_pack_refs_succeeds_with_existing_stash_and_multiple_worktrees(
        self, tmp_path: Path
    ) -> None:
        """A maintenance `pack-refs` rewrite of an existing `refs/stash`
        (same old/new value) is let through, unblocking `git gc`, even
        though a second worktree is registered."""
        root = tmp_path / "repo"
        _init_repo(root)
        (root / "frob.toml").write_text("[project]\n")
        apply_managed_blocks(root)

        # Create a stash while still the only worktree (stash itself must
        # be allowed here -- n == 1).
        (root / "README.md").write_text("changed\n")
        stash_result = _git("stash", "push", "-q", cwd=root)
        assert stash_result.returncode == 0, stash_result.stderr

        # Register a second worktree so the guard's n > 1 branch is live.
        other = tmp_path / "other-wt"
        wt_result = _git(
            "worktree", "add", "-q", "-b", "other", str(other), "main", cwd=root
        )
        assert wt_result.returncode == 0, wt_result.stderr

        # A maintenance pack-refs rewrite of the existing refs/stash (and
        # everything else) must succeed -- this is the T-0870 regression.
        pack_result = _git("pack-refs", "--all", cwd=root)
        assert pack_result.returncode == 0, pack_result.stderr

        gc_result = _git("gc", cwd=root)
        assert gc_result.returncode == 0, gc_result.stderr

    # frob:ticket T-0870
    # frob:tests tests/unit/test_scaffold_stash_guard.py::TestStashGuardPackRefs.test_stash_still_refused_with_multiple_worktrees  # noqa: E501
    def test_stash_still_refused_with_multiple_worktrees(self, tmp_path: Path) -> None:
        """A genuine `git stash push` (the ref's value actually changes)
        is still refused once a second worktree exists -- the pack-refs
        fix must not weaken the original T-0574 guard."""
        root = tmp_path / "repo"
        _init_repo(root)
        (root / "frob.toml").write_text("[project]\n")
        apply_managed_blocks(root)

        other = tmp_path / "other-wt"
        wt_result = _git(
            "worktree", "add", "-q", "-b", "other", str(other), "main", cwd=root
        )
        assert wt_result.returncode == 0, wt_result.stderr

        (root / "README.md").write_text("changed again\n")
        stash_result = _git("stash", "push", "-q", cwd=root)
        assert stash_result.returncode != 0
        assert "refusing 'git stash'" in stash_result.stderr
        assert "agent-playbook.md#1b" in stash_result.stderr
