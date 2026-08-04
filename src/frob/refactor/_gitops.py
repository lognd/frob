"""Shared git primitives for `frob.refactor`'s own transaction commits and
rollbacks (docs/design/refactor-verb.md's Transaction model): one WIP
commit per applied transaction, `git reset --hard` back to a captured
pre-transaction sha on any verify failure. Split out of `_transaction.py`
(T-1201) so `_split.py`'s own per-chunk transactions reuse the identical
git primitives instead of a second copy (CLAUDE.md's no-duplication rule)
-- never `git stash` (agent-playbook.md sec 1b).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.process._guard import guarded_subprocess_run
from frob.refactor._models import RefactorError

__all__ = ["current_sha", "git", "working_tree_clean"]


# frob:doc docs/commands/refactor.md#git
def git(repo_root: Path, *args: str, timeout: int = 30):
    """One `git` invocation inside `repo_root`, routed through the same
    exec kill-switch every other subprocess call in this package uses."""
    return guarded_subprocess_run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# frob:doc docs/commands/refactor.md#working_tree_clean
# frob:tests tests/test_refactor.py::TestGitOps.test_working_tree_clean_true_when_no_changes kind="unit"  # noqa: E501
# frob:tests tests/test_refactor.py::TestGitOps.test_working_tree_clean_false_when_dirty kind="unit"  # noqa: E501
def working_tree_clean(repo_root: Path) -> Result[bool, RefactorError]:
    """`True` iff `git status --porcelain` is empty -- the precondition
    every transaction (single move/rename or a split chunk) assumes before
    it starts writing."""
    result = git(repo_root, "status", "--porcelain")
    if result.is_err:
        return Err(RefactorError.GitError)
    proc = result.danger_ok
    if proc.returncode != 0:
        return Err(RefactorError.NotAGitRepo)
    return Ok(proc.stdout.strip() == "")


# frob:doc docs/commands/refactor.md#current_sha
# frob:tests tests/test_refactor.py::TestGitOps.test_current_sha_matches_head \
# kind="unit"
def current_sha(repo_root: Path) -> Result[str, RefactorError]:
    """The `HEAD` sha a transaction rolls back to on failure."""
    result = git(repo_root, "rev-parse", "HEAD")
    if result.is_err or result.danger_ok.returncode != 0:
        return Err(RefactorError.GitError)
    return Ok(result.danger_ok.stdout.strip())
