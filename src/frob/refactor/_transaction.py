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
from frob.refactor._alias_policy import resolve_rename_dest_collision
from frob.refactor._apply import apply_plan, build_move_ops
from frob.refactor._directives import (
    carry_lock_acks,
    extend_span_for_attached_directives,
    scan_directive_carriers,
)
from frob.refactor._models import (
    AliasRecord,
    RefactorError,
    RefactorKind,
    RefactorPlan,
    RefactorReport,
    RewriteOp,
    SymbolRef,
    VerifyOutcome,
)
from frob.refactor._prose import (
    scan_doc_anchor_carriers,
    scan_docs_prose_mentions,
    scan_python_prose_mentions,
)
from frob.refactor._repointer import (
    scan_evidence_citations,
    scan_pii_allowlist_carrier,
    scan_registry_citations,
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


def _colliding_destination_symbol(repo_root: Path, resolved, destination: SymbolRef):
    """The `ResolvedSymbol` already occupying `destination`'s leaf name, if
    one exists and is not merely `resolved` itself (the expected in-place
    case for e.g. a same-module rename) -- `None` when there is no real
    collision. Split out of `build_plan` (via `_destination_collision`) to
    keep it under the ARCH001 line budget."""
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
    return None if is_self else existing


def _destination_collision(
    repo_root: Path, resolved, destination: SymbolRef, alias_conflict: str
) -> tuple[RefactorError | None, list[RewriteOp], AliasRecord | None]:
    """T-1202's alias-conflict policy dispatch: `(error, extra_ops,
    alias)` -- `error` is `DestinationCollision` (and the other two are
    empty/`None`) under the default `error` policy, or `None` plus the
    `rename-dest` resolution's own ops/alias when `alias_conflict ==
    'rename-dest'` and a real collision exists. No collision at all
    yields `(None, [], None)` either way."""
    existing = _colliding_destination_symbol(repo_root, resolved, destination)
    if existing is None:
        return None, [], None
    dest_leaf = destination.qualname.split(".")[-1]
    if alias_conflict != "rename-dest":
        _log.warning(
            "refactor.plan: destination collision at %s::%s",
            destination.module,
            dest_leaf,
        )
        return RefactorError.DestinationCollision, [], None
    _log.info(
        "refactor.plan: destination collision at %s::%s resolved via rename-dest",
        destination.module,
        dest_leaf,
    )
    own_rename_op, caller_ops, alias = resolve_rename_dest_collision(
        repo_root, existing, dest_leaf
    )
    return None, [own_rename_op, *caller_ops], alias


def _prose_carrier_ops(
    repo_root: Path, resolved, destination: SymbolRef
) -> tuple[list, list[str]]:
    """T-1267's three free-text carriers, folded into one call so
    `build_plan` stays under the ARCH001 line budget -- mirrors the T-1200
    trio's own inline shape in `build_plan`, just split out since this is
    the fourth carrier group added to the same function."""
    prose_ops, prose_unresolved = scan_python_prose_mentions(
        repo_root, resolved, destination
    )
    docs_ops, docs_unresolved = scan_docs_prose_mentions(
        repo_root, resolved, destination
    )
    anchor_ops, anchor_unresolved = scan_doc_anchor_carriers(
        repo_root, resolved, destination
    )
    ops = prose_ops + docs_ops + anchor_ops
    unresolved = prose_unresolved + docs_unresolved + anchor_unresolved
    return ops, unresolved


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
    sibling pass (T-1199/T-1200/T-1267) can extend `reference_ops`
    against an already-built plan without re-running Resolve.
    """
    resolved_result = resolve_symbol(repo_root, source)
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved = resolved_result.danger_ok

    collision_error, collision_ops, collision_alias = _destination_collision(
        repo_root, resolved, destination, alias_conflict
    )
    if collision_error is not None:
        return Err(collision_error)

    # T-1199: a `frob:*` directive/waiver comment block attached directly
    # above the symbol's own definition line moves WITH it -- extend the
    # move span before computing the move ops, since `ast`'s own
    # lineno/end_lineno never includes leading comment lines.
    source_lines = Path(resolved.file_path).read_text(encoding="utf-8").splitlines()
    move_start = extend_span_for_attached_directives(source_lines, resolved.start_line)

    delete_op, append_op = build_move_ops(
        repo_root,
        resolved.file_path,
        move_start,
        resolved.end_line,
        destination.module,
        destination.qualname.split(".")[-1],
        source.qualname.split(".")[-1],
    )
    reference_ops, aliases, unresolved = scan_references(
        repo_root, resolved, destination, alias_conflict=alias_conflict
    )
    # T-1199: repo-wide `frob:*` directive TARGET/SRC carrier -- a
    # directive elsewhere in the repo naming this symbol's old symref gets
    # repointed at its new one.
    directive_ops, directive_unresolved = scan_directive_carriers(
        repo_root, resolved, destination
    )
    reference_ops = list(reference_ops) + directive_ops
    unresolved = list(unresolved) + directive_unresolved

    # T-1200: the three non-DSL reference kinds the directive carrier
    # cannot reach -- PII012 allowlist, registry citations, ticket
    # evidence -- each a text-level literal-substring rewrite of the
    # moving symbol's old symref.
    pii_ops, pii_unresolved = scan_pii_allowlist_carrier(
        repo_root, resolved, destination
    )
    registry_ops, registry_unresolved = scan_registry_citations(
        repo_root, resolved, destination
    )
    evidence_ops, evidence_unresolved = scan_evidence_citations(
        repo_root, resolved, destination
    )
    reference_ops = list(reference_ops) + pii_ops + registry_ops + evidence_ops
    unresolved = (
        list(unresolved) + pii_unresolved + registry_unresolved + evidence_unresolved
    )

    # T-1267: the free-text reference kinds no structured carrier reaches
    # -- python docstring/comment prose, docs/** prose, and doc heading/
    # anchor slug rewrites.
    prose_ops, prose_unresolved = _prose_carrier_ops(repo_root, resolved, destination)
    reference_ops = reference_ops + prose_ops
    unresolved = unresolved + prose_unresolved

    # T-1202: `--alias-conflict rename-dest`'s own resolution ops/alias,
    # if a destination-namespace collision existed and that policy was
    # selected (empty/`None` otherwise, including the default `error`
    # policy where a real collision already returned `Err` above).
    reference_ops = reference_ops + collision_ops
    aliases = list(aliases) + ([collision_alias] if collision_alias is not None else [])

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

    # T-1199: carry any frob.lock ack keyed on the moving symbol's old
    # symref forward to its new one, BEFORE the WIP commit so the carried
    # lock file is captured by the same `git add -A` and reverted together
    # with everything else on a verify-failure rollback.
    carry_lock_acks(repo_root, plan.source, destination)

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
