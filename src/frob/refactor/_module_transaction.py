"""`frob refactor move-module` transaction orchestrator (T-2990):
resolve -> validate destination -> plan -> apply -> `git mv` -> commit
-> verify -> commit-or-rollback, the module-move mirror of
`_transaction.run_refactor`.

REUSE, not a second copy of the parts that are genuinely kind-agnostic:
`_gitops` (as-is), `_apply.apply_plan` (as-is -- it splices any file's
line spans, Python or not), `_commit.commit_wip`/`run_verify_outcomes`
(as-is, factored out of `_transaction.py` for exactly this), and
`_operands`'s typed-operand parsing/destination validation (as-is).

NOT reused: `_resolve.resolve_symbol` (a module has no `qualname` to
resolve within a file -- the whole FILE is the target) and `_scan.
scan_references`/`_apply.build_move_ops` (both are symbol-span-shaped:
one deletes/inserts a line RANGE inside a file, the other only
rewrites `from <module> import <qualname>`; neither has anything to do
for a module move, whose "move op" is `git mv` on the whole file and
whose reference scan must find `import module`/`from pkg import
module` forms `_scan.py` never looks for at all). This is the "too
symbol-shaped to factor cleanly" boundary T-2990 asked to have named
explicitly rather than forced -- see `_module_scan_python.py`'s module
docstring for the full reference-kind inventory this module needed
instead.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.refactor._apply import apply_ops
from frob.refactor._commit import commit_wip, run_verify_outcomes
from frob.refactor._gitops import current_sha, git, working_tree_clean
from frob.refactor._models import RefactorError, RewriteOp, VerifyOutcome
from frob.refactor._module_lang import adapter_for
from frob.refactor._module_prose import scan_module_path_citations
from frob.refactor._module_resolve import ResolvedModule, resolve_module
from frob.refactor._operands import ModuleRef, OperandError, validate_module_destination

_log = get_logger(__name__)

__all__ = ["ModulePlan", "ModuleRefactorReport", "build_module_plan", "run_move_module"]


def _display_path(repo_root: Path, path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given --
    matches every other scan module's own convention in this package."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


# frob:doc docs/commands/refactor.md#moduleplan
# frob:tests \
# tests/test_refactor.py::TestBuildModulePlan.test_plan_includes_reference_ops
class ModulePlan(BaseModel):
    """The full module-move rewrite plan, computed once before any file
    write -- the module-verb mirror of `RefactorPlan`. `reference_ops`
    covers every reference kind (Python AST forms plus non-Python
    citations); there is no `move_ops` field because the move itself is
    a single `git mv`, not a set of line-span splices."""

    model_config = ConfigDict(frozen=True)

    source: ResolvedModule
    destination: ModuleRef
    destination_path: str
    reference_ops: tuple[RewriteOp, ...]
    unresolved: tuple[str, ...] = ()

    # frob:doc docs/commands/refactor.md#moduleplan
    @property
    def touched_files(self) -> tuple[Path, ...]:
        """Every file path any reference op writes to, plus the source
        and destination file themselves -- the Verify phase's scoping
        input, mirroring `RefactorPlan.touched_files`."""
        seen: dict[str, None] = {}
        for op in self.reference_ops:
            seen.setdefault(op.file_path, None)
        seen.setdefault(self.source.file_path, None)
        seen.setdefault(self.destination_path, None)
        return tuple(Path(p) for p in seen)


# frob:doc docs/commands/refactor.md#modulerefactorreport
# frob:tests tests/test_refactor.py::TestRunMoveModule.test_move_module_succeeds_and_commits  # noqa: E501
class ModuleRefactorReport(BaseModel):
    """The disclosed report for a `move-module` transaction -- the
    module-verb mirror of `RefactorReport`."""

    model_config = ConfigDict(frozen=True)

    plan: ModulePlan
    verify_outcomes: tuple[VerifyOutcome, ...]
    pre_sha: str
    commit_sha: str | None
    success: bool
    rolled_back: bool


# frob:doc docs/commands/refactor.md#build_module_plan
# frob:tests \
# tests/test_refactor.py::TestBuildModulePlan.test_plan_includes_reference_ops
# frob:tests \
# tests/test_refactor.py::TestBuildModulePlan.test_refuses_unsupported_language
def build_module_plan(
    repo_root: Path,
    source: ModuleRef,
    destination: ModuleRef,
    *,
    allow_existing: bool = False,
) -> Result[ModulePlan, RefactorError]:
    """Plan phase entry point: resolve `source` (confirms the file
    exists and its language has a registered adapter -- `_module_
    resolve.resolve_module`), validate `destination` as a legal Python
    module location (`_operands.validate_module_destination`), then
    dispatch to the source language's `ModuleReferenceScanner` for the
    reference rewrite inventory plus the shared non-Python citation
    scan (`_module_prose.scan_module_path_citations`)."""
    resolved_result = resolve_module(repo_root, source)
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved = resolved_result.danger_ok

    dest_result = validate_module_destination(
        repo_root, destination, allow_existing=allow_existing
    )
    if dest_result.is_err:
        operand_err = dest_result.danger_err
        mapped = (
            RefactorError.DestinationCollision
            if operand_err == OperandError.DestinationExists
            else RefactorError.TargetNotFound
        )
        _log.warning(
            "refactor.module_plan: destination %s refused: %s",
            destination.module,
            operand_err,
        )
        return Err(mapped)
    dest_path = dest_result.danger_ok

    adapter = adapter_for(resolved.language)
    assert adapter is not None  # resolve_module already confirmed this
    lang_ops, _lang_aliases, lang_unresolved = adapter(repo_root, resolved, destination)

    old_rel = _display_path(repo_root, Path(resolved.file_path))
    new_rel = _display_path(repo_root, dest_path)
    prose_ops, prose_unresolved = scan_module_path_citations(
        repo_root, source.module, destination.module, old_rel, new_rel
    )

    plan = ModulePlan(
        source=resolved,
        destination=destination,
        destination_path=str(dest_path),
        reference_ops=tuple(lang_ops) + tuple(prose_ops),
        unresolved=tuple(lang_unresolved) + tuple(prose_unresolved),
    )
    _log.info(
        "refactor.module_plan: %s -> %s: %d reference op(s), %d unresolved",
        source.module,
        destination.module,
        len(plan.reference_ops),
        len(plan.unresolved),
    )
    return Ok(plan)


def _apply_module_plan(
    repo_root: Path, plan: ModulePlan
) -> Result[None, RefactorError]:
    """Splice every reference op into its target file via `_apply.
    apply_ops` (T-2990: the SAME per-file splice-and-overlap-guard
    mechanics `_transaction.py`'s symbol pipeline uses, reused not
    forked). Edits land IN the source file's current (pre-move) path;
    `git mv` below relocates the already-edited content, matching
    `apply_plan`'s own write-then-move ordering."""
    del repo_root
    return apply_ops(plan.reference_ops)


def _verify_no_surviving_references(repo_root: Path, old_module: str) -> VerifyOutcome:
    """T-2990's module-move-specific post-condition: `git grep -c` for a
    literal occurrence of the OLD dotted module path anywhere in the
    tracked tree, after the transaction has applied and committed. A
    partial rename -- something no reference-kind scan above caught --
    is exactly the failure mode this exists to catch; a real hit rolls
    the whole transaction back rather than landing a half-renamed
    module. Scoped to the exact dotted path (never a bare leaf name),
    so an unrelated prose mention that never spells the full module
    path is not a false positive here. `-w` (whole-word) keeps this
    scoped to the same boundary guarantee `_module_prose.py`'s own scan
    makes -- `pkg.old_mod` must never register a hit inside a
    prefix-colliding sibling like `pkg.old_mod_extra`."""
    result = git(repo_root, "grep", "-c", "-w", old_module)
    if result.is_err:
        return VerifyOutcome(
            name="no_surviving_references",
            passed=False,
            detail=f"could not run git grep: {result.danger_err}",
        )
    proc = result.danger_ok
    # `git grep` exits 1 when there are no matches (success for us), 0
    # when there ARE matches (failure for us), >1 on a real error.
    if proc.returncode == 1:
        return VerifyOutcome(
            name="no_surviving_references",
            passed=True,
            detail=f"no remaining occurrence of {old_module!r} in the tracked tree",
        )
    if proc.returncode == 0:
        return VerifyOutcome(
            name="no_surviving_references",
            passed=False,
            detail=f"{old_module!r} still occurs:\n{proc.stdout[-2000:]}",
        )
    return VerifyOutcome(
        name="no_surviving_references",
        passed=False,
        detail=f"git grep failed unexpectedly (rc={proc.returncode}): "
        f"{proc.stderr[-500:]}",
    )


def _resolve_and_plan_module(
    repo_root: Path, source: ModuleRef, destination: ModuleRef, allow_existing: bool
) -> Result[tuple[str, ModulePlan], RefactorError]:
    """`run_move_module`'s precondition-then-plan preamble: confirm a
    clean tree, capture the pre-transaction sha, then `build_module_
    plan`. Split out (ARCH001, T-2990) to mirror `_transaction.
    _resolve_and_plan`'s identical shape for the symbol pipeline."""
    clean_result = working_tree_clean(repo_root)
    if clean_result.is_err:
        return Err(clean_result.danger_err)
    if not clean_result.danger_ok:
        return Err(RefactorError.DirtyWorkingTree)

    sha_result = current_sha(repo_root)
    if sha_result.is_err:
        return Err(sha_result.danger_err)
    pre_sha = sha_result.danger_ok

    plan_result = build_module_plan(
        repo_root, source, destination, allow_existing=allow_existing
    )
    if plan_result.is_err:
        return Err(plan_result.danger_err)
    return Ok((pre_sha, plan_result.danger_ok))


def _apply_and_move(repo_root: Path, plan: ModulePlan) -> Result[None, RefactorError]:
    """Apply every reference op, then `git mv` the source file itself
    (preserving rename detection -- T-2990's explicit ask, unlike a
    symbol-move loop's delete+recreate). Split out of `run_move_module`
    (ARCH001) -- a failure at either step reverts the uncommitted
    working tree, matching `run_refactor`'s own apply-failure recovery."""
    apply_result = _apply_module_plan(repo_root, plan)
    if apply_result.is_err:
        git(repo_root, "checkout", "--", ".")
        git(repo_root, "clean", "-fd", "--", *(str(p) for p in plan.touched_files))
        return Err(apply_result.danger_err)

    mv_result = git(repo_root, "mv", plan.source.file_path, plan.destination_path)
    if mv_result.is_err or mv_result.danger_ok.returncode != 0:
        git(repo_root, "checkout", "--", ".")
        git(repo_root, "clean", "-fd", "--", *(str(p) for p in plan.touched_files))
        return Err(RefactorError.GitError)
    return Ok(None)


# frob:doc docs/commands/refactor.md#run_move_module
# frob:tests tests/test_refactor.py::TestRunMoveModule.test_move_module_succeeds_and_commits  # noqa: E501
# frob:tests tests/test_refactor.py::TestRunMoveModule.test_move_module_rolls_back_on_verify_failure  # noqa: E501
# frob:tests tests/test_refactor.py::TestRunMoveModule.test_move_module_uses_git_mv
def run_move_module(
    repo_root: Path,
    source: ModuleRef,
    destination: ModuleRef,
    *,
    run_pytest_collect: bool = True,
    run_check_delta: bool = True,
    pytest_scope_touched_only: bool = True,
    allow_existing: bool = False,
) -> Result[ModuleRefactorReport, RefactorError]:
    """The full `move-module` pipeline: Resolve+Plan (`build_module_
    plan`), Apply (reference rewrites), `git mv` the file itself
    (preserving rename detection -- T-2990's explicit ask, unlike a
    symbol-move loop's delete+recreate), commit, then the shared
    Verify-phase post-conditions (`_commit.run_verify_outcomes`) PLUS
    this verb's own `_verify_no_surviving_references` -- commit-or-
    rollback exactly like `_transaction.run_refactor`."""
    preamble_result = _resolve_and_plan_module(
        repo_root, source, destination, allow_existing
    )
    if preamble_result.is_err:
        return Err(preamble_result.danger_err)
    pre_sha, plan = preamble_result.danger_ok

    apply_result = _apply_and_move(repo_root, plan)
    if apply_result.is_err:
        return Err(apply_result.danger_err)

    commit_msg = f"wip(refactor): move-module {source.module} -> {destination.module}"
    commit_sha_result = commit_wip(repo_root, commit_msg, pre_sha)
    if commit_sha_result.is_err:
        return Err(commit_sha_result.danger_err)
    commit_sha = commit_sha_result.danger_ok or None

    outcomes = run_verify_outcomes(
        repo_root,
        list(plan.touched_files),
        run_pytest_collect,
        run_check_delta,
        pytest_scope_touched_only,
    )
    outcomes.append(_verify_no_surviving_references(repo_root, source.module))

    success = all(outcome.passed for outcome in outcomes)
    rolled_back = False
    if not success:
        _log.warning(
            "refactor.module_transaction: verify failed, rolling back to %s", pre_sha
        )
        reset_result = git(repo_root, "reset", "--hard", pre_sha)
        rolled_back = reset_result.is_ok and reset_result.danger_ok.returncode == 0

    report = ModuleRefactorReport(
        plan=plan,
        verify_outcomes=tuple(outcomes),
        pre_sha=pre_sha,
        commit_sha=None if rolled_back else commit_sha,
        success=success,
        rolled_back=rolled_back,
    )
    _log.info(
        "refactor.module_transaction: move-module complete success=%s rolled_back=%s",
        success,
        rolled_back,
    )
    return Ok(report)
