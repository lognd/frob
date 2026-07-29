"""Transaction orchestrator: resolve -> plan -> apply -> verify ->
commit-or-rollback, the whole `frob refactor` pipeline in one call
(docs/design/refactor-verb.md's Transaction model).

Never `git stash` (agent-playbook.md sec 1b) -- rollback is a scoped `git
reset --hard` to this transaction's own pre-commit sha, exactly as the
design doc specifies.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.refactor._apply import apply_plan, build_move_ops
from frob.refactor._models import (
    RefactorError,
    RefactorKind,
    RefactorPlan,
    RefactorReport,
    SymbolRef,
    VerifyOutcome,
)
from frob.refactor._resolve import module_to_path, resolve_symbol
from frob.refactor._scan import scan_references
from frob.refactor._verify import (
    verify_check_delta,
    verify_import_resolution,
    verify_pytest_collect,
)

_log = get_logger(__name__)

__all__ = ["build_plan", "run_refactor"]


def _git(repo_root: Path, *args: str, timeout: int = 30):
    """One `git` invocation inside `repo_root`, routed through the same
    exec kill-switch every other subprocess call in this package uses."""
    return guarded_subprocess_run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _working_tree_clean(repo_root: Path) -> Result[bool, RefactorError]:
    """`True` iff `git status --porcelain` is empty -- the precondition
    the design doc's Transaction model assumes (the caller's own worktree
    commit discipline, not this engine's job to enforce by committing
    unrelated WIP for them)."""
    result = _git(repo_root, "status", "--porcelain")
    if result.is_err:
        return Err(RefactorError.GitError)
    proc = result.danger_ok
    if proc.returncode != 0:
        return Err(RefactorError.NotAGitRepo)
    return Ok(proc.stdout.strip() == "")


def _current_sha(repo_root: Path) -> Result[str, RefactorError]:
    """The `HEAD` sha this transaction will roll back to on failure."""
    result = _git(repo_root, "rev-parse", "HEAD")
    if result.is_err or result.danger_ok.returncode != 0:
        return Err(RefactorError.GitError)
    return Ok(result.danger_ok.stdout.strip())


def _destination_collision(
    repo_root: Path, resolved, destination: SymbolRef
) -> RefactorError | None:
    """`DestinationCollision` iff `destination` already names a distinct
    symbol at the destination module (not merely `resolved` itself,
    which is the expected in-place case for e.g. a same-module rename).
    Split out of `build_plan` to keep it under the ARCH001 line budget.
    """
    dest_file = module_to_path(repo_root, destination.module)
    if not dest_file.is_file():
        return None
    dest_leaf = destination.qualname.split(".")[-1]
    existing_result = resolve_symbol(
        repo_root, SymbolRef(module=destination.module, qualname=dest_leaf)
    )
    if existing_result.is_err:
        return None
    existing = existing_result.danger_ok
    is_self = (
        existing.file_path == resolved.file_path
        and existing.start_line == resolved.start_line
        and existing.end_line == resolved.end_line
    )
    if is_self:
        return None
    _log.warning(
        "refactor.plan: destination collision at %s::%s",
        destination.module,
        dest_leaf,
    )
    return RefactorError.DestinationCollision


# frob:doc docs/commands/refactor.md#build_plan
# frob:tests tests/test_refactor.py::TestBuildPlan.test_plan_includes_move_and_reference_ops  # noqa: E501
def build_plan(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    alias_conflict: str = "error",
) -> Result[RefactorPlan, RefactorError]:
    """Plan phase entry point: resolve `source`, refuse on a destination
    collision, then build every move-op and reference-op before any file
    is written. Exposed standalone (not only via `run_refactor`) so a
    sibling pass (T-1199/T-1200/T-1203) can extend `reference_ops`
    against an already-built plan without re-running Resolve.
    """
    resolved_result = resolve_symbol(repo_root, source)
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved = resolved_result.danger_ok

    collision = _destination_collision(repo_root, resolved, destination)
    if collision is not None:
        return Err(collision)

    delete_op, append_op = build_move_ops(
        repo_root,
        resolved.file_path,
        resolved.start_line,
        resolved.end_line,
        destination.module,
        destination.qualname.split(".")[-1],
        source.qualname.split(".")[-1],
    )
    reference_ops, aliases, unresolved = scan_references(
        repo_root, resolved, destination, alias_conflict=alias_conflict
    )
    plan = RefactorPlan(
        kind=kind,
        source=resolved,
        destination=destination,
        move_ops=(delete_op, append_op),
        reference_ops=tuple(reference_ops),
        aliases=tuple(aliases),
        unresolved=tuple(unresolved),
    )
    _log.info(
        "refactor.plan: %s -> %s: %d reference op(s), %d alias(es), %d unresolved",
        source.dotted,
        destination.dotted,
        len(plan.reference_ops),
        len(plan.aliases),
        len(plan.unresolved),
    )
    return Ok(plan)


def _commit_plan(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    pre_sha: str,
) -> Result[str, RefactorError]:
    """`git add -A` + `git commit` the applied plan as one WIP commit;
    `git reset --hard pre_sha` and `Err(GitError)` on either step
    failing. Split out of `run_refactor` to keep it under the ARCH001
    line budget.
    """
    commit_result = _git(repo_root, "add", "-A")
    if commit_result.is_err or commit_result.danger_ok.returncode != 0:
        _git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    commit_msg = f"wip(refactor): {kind.value} {source.dotted} -> {destination.dotted}"
    commit_result = _git(repo_root, "commit", "-m", commit_msg)
    if commit_result.is_err or commit_result.danger_ok.returncode != 0:
        _git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    commit_sha_result = _current_sha(repo_root)
    return Ok(commit_sha_result.danger_ok if commit_sha_result.is_ok else "")


def _run_verify(
    repo_root: Path,
    plan: RefactorPlan,
    run_pytest_collect: bool,
    run_check_delta: bool,
    pytest_scope_touched_only: bool,
) -> list[VerifyOutcome]:
    """Run the three Verify-phase post-conditions the design doc
    specifies (import resolution, pytest collection, `frob check
    --delta`), each individually skippable by the caller's own flags.
    Split out of `run_refactor` to keep it under the ARCH001 line
    budget.
    """
    outcomes: list[VerifyOutcome] = [
        verify_import_resolution(list(plan.touched_files), repo_root=repo_root)
    ]
    if run_pytest_collect:
        targets = list(plan.touched_files) if pytest_scope_touched_only else None
        outcomes.append(verify_pytest_collect(repo_root, targets=targets))
    if run_check_delta:
        outcomes.append(verify_check_delta(repo_root))
    return outcomes


def _resolve_and_plan(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    alias_conflict: str,
) -> Result[tuple[str, RefactorPlan], RefactorError]:
    """`run_refactor`'s precondition-then-plan preamble: confirm a clean
    tree, capture the pre-transaction sha, then `build_plan`. Split out
    of `run_refactor` to keep it under the ARCH001 line budget."""
    clean_result = _working_tree_clean(repo_root)
    if clean_result.is_err:
        return Err(clean_result.danger_err)
    if not clean_result.danger_ok:
        return Err(RefactorError.DirtyWorkingTree)

    sha_result = _current_sha(repo_root)
    if sha_result.is_err:
        return Err(sha_result.danger_err)
    pre_sha = sha_result.danger_ok

    plan_result = build_plan(repo_root, kind, source, destination, alias_conflict)
    if plan_result.is_err:
        return Err(plan_result.danger_err)
    return Ok((pre_sha, plan_result.danger_ok))


# frob:doc docs/commands/refactor.md#run_refactor
# frob:tests tests/test_refactor.py::TestRunRefactor.test_rename_succeeds_and_commits
# frob:tests tests/test_refactor.py::TestRunRefactor.test_verify_failure_rolls_back
def run_refactor(
    repo_root: Path,
    kind: RefactorKind,
    source: SymbolRef,
    destination: SymbolRef,
    alias_conflict: str = "error",
    run_pytest_collect: bool = True,
    run_check_delta: bool = True,
    pytest_scope_touched_only: bool = True,
) -> Result[RefactorReport, RefactorError]:
    """The full pipeline in one call: Resolve+Plan (`build_plan`), Apply
    (`apply_plan`), Verify (the three `_verify` post-conditions), then
    commit or `git reset --hard` back to the pre-transaction sha. Returns
    `Err` only for a precondition that refuses before any write (dirty
    tree, not a git repo, target does not resolve, destination collides);
    once a transaction has actually applied writes, every outcome --
    including a rolled-back one -- comes back as `Ok(RefactorReport)` with
    `success`/`rolled_back` set, per the design doc's "prints the
    disclosed report either way" rule.
    """
    preamble_result = _resolve_and_plan(
        repo_root, kind, source, destination, alias_conflict
    )
    if preamble_result.is_err:
        return Err(preamble_result.danger_err)
    pre_sha, plan = preamble_result.danger_ok

    apply_result = apply_plan(repo_root, plan)
    if apply_result.is_err:
        # Nothing was committed yet; a partial write here would still be
        # uncommitted, so a plain reset (not reset --hard, no commit
        # exists yet to reset past) is enough to restore a clean tree.
        _git(repo_root, "checkout", "--", ".")
        _git(repo_root, "clean", "-fd", "--", *(str(p) for p in plan.touched_files))
        # Propagate apply_plan's own error value (e.g. OverlappingRewrites
        # detected before any write, vs. an OSError mid-write surfacing as
        # ApplyFailed) rather than collapsing every apply-phase failure
        # into ApplyFailed -- a caller branching on RefactorError needs to
        # tell these apart.
        return Err(apply_result.danger_err)

    commit_sha_result = _commit_plan(repo_root, kind, source, destination, pre_sha)
    if commit_sha_result.is_err:
        return Err(commit_sha_result.danger_err)
    commit_sha = commit_sha_result.danger_ok or None

    outcomes = _run_verify(
        repo_root, plan, run_pytest_collect, run_check_delta, pytest_scope_touched_only
    )

    success = all(outcome.passed for outcome in outcomes)
    rolled_back = False
    if not success:
        _log.warning("refactor.transaction: verify failed, rolling back to %s", pre_sha)
        reset_result = _git(repo_root, "reset", "--hard", pre_sha)
        rolled_back = reset_result.is_ok and reset_result.danger_ok.returncode == 0

    report = RefactorReport(
        plan=plan,
        verify_outcomes=tuple(outcomes),
        pre_sha=pre_sha,
        commit_sha=None if rolled_back else commit_sha,
        success=success,
        rolled_back=rolled_back,
    )
    _log.info(
        "refactor.transaction: %s complete success=%s rolled_back=%s",
        kind.value,
        success,
        rolled_back,
    )
    return Ok(report)
