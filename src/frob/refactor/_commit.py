"""Shared commit-or-rollback primitives (T-2990): the WIP-commit-then-
verify-then-reset-hard shape `_transaction.py`'s symbol pipeline already
implements, factored out so `_module_transaction.py`'s module-move
pipeline calls the SAME functions rather than a second copy -- this
repo's own no-duplication rule, applied to the one piece of the
existing engine that genuinely is language/kind-agnostic (unlike
`_scan.py`'s reference-rewriting, which is symbol-shaped and NOT reused
here; see `_module_scan_python.py`'s module docstring for why).
"""

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.refactor._gitops import current_sha, git
from frob.refactor._models import RefactorError, VerifyOutcome
from frob.refactor._verify import (
    verify_check_delta,
    verify_import_resolution,
    verify_pytest_collect,
)

__all__ = ["commit_wip", "run_verify_outcomes"]


# frob:doc docs/commands/refactor.md#commit_wip
# frob:tests tests/test_refactor.py::TestCommit.test_commit_wip_commits_and_returns_sha
# frob:tests tests/test_refactor.py::TestCommit.test_commit_wip_resets_on_git_failure
def commit_wip(
    repo_root: Path, message: str, pre_sha: str
) -> Result[str, RefactorError]:
    """`git add -A` + `git commit -m message`; `git reset --hard pre_sha`
    and `Err(GitError)` on either step failing. The one WIP-commit shape
    every `frob refactor` transaction (symbol move/rename, `split`
    chunk, module move) performs identically."""
    add_result = git(repo_root, "add", "-A")
    if add_result.is_err or add_result.danger_ok.returncode != 0:
        git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    commit_result = git(repo_root, "commit", "-m", message)
    if commit_result.is_err or commit_result.danger_ok.returncode != 0:
        git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    sha_result = current_sha(repo_root)
    return Ok(sha_result.danger_ok if sha_result.is_ok else "")


# frob:doc docs/commands/refactor.md#run_verify_outcomes
# frob:tests tests/test_refactor.py::TestCommit.test_run_verify_outcomes_runs_requested_checks  # noqa: E501
def run_verify_outcomes(
    repo_root: Path,
    touched_files: list[Path],
    run_pytest_collect: bool,
    run_check_delta: bool,
    pytest_scope_touched_only: bool,
) -> list[VerifyOutcome]:
    """Run the Verify-phase post-conditions common to every `frob
    refactor` transaction (import resolution, optionally pytest
    collection and `frob check --delta`), each individually skippable --
    the same three checks `_transaction.py`'s symbol pipeline runs,
    factored here so `_module_transaction.py` calls this instead of
    re-deriving the same three-line sequence."""
    outcomes: list[VerifyOutcome] = [
        verify_import_resolution(touched_files, repo_root=repo_root)
    ]
    if run_pytest_collect:
        targets = touched_files if pytest_scope_touched_only else None
        outcomes.append(verify_pytest_collect(repo_root, targets=targets))
    if run_check_delta:
        outcomes.append(verify_check_delta(repo_root))
    return outcomes
