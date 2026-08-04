"""`frob refactor split`: move N symbols out of one module into a new
sibling module in chunked, individually refuse-and-rollback-safe
transactions, generating a re-export shim in the source module so every
external `from source import symbol` call site needs no edit (docs/design/
refactor-verb.md child 4, T-1135 -- the T-1072/T-1077 manual family-
extraction pattern made mechanical).

Each chunk plans a move for every symbol in it via `build_plan` (T-1197's
resolve/plan pipeline, already carrying every T-1199/T-1200/T-1267 carrier
pass), merges all of that chunk's ops into one `apply_plan` call plus one
re-export-shim append op, and verifies/commits/rolls back the WHOLE chunk
as a single transaction -- never a partial chunk. A later chunk's failure
never touches an earlier chunk's already-committed symbols (the epic's
acceptance [1]).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.refactor._apply import apply_plan
from frob.refactor._directives import carry_lock_acks
from frob.refactor._gitops import current_sha, git, working_tree_clean
from frob.refactor._models import (
    AliasRecord,
    RefactorError,
    RefactorKind,
    RefactorPlan,
    RewriteOp,
    SymbolRef,
    VerifyOutcome,
)
from frob.refactor._resolve import module_to_path
from frob.refactor._transaction import build_plan
from frob.refactor._verify import (
    verify_check_delta,
    verify_import_resolution,
    verify_pytest_collect,
)

_log = get_logger(__name__)

__all__ = [
    "ChunkReport",
    "SplitReport",
    "build_reexport_shim_op",
    "chunk_symbols",
    "run_split",
]

# frob:doc docs/commands/refactor.md#split-verb-t-1201
DEFAULT_CHUNK_SIZE = 5
"""Default max symbols moved per apply-and-verify chunk transaction
(`chunk_symbols`'s own `chunk_size` default)."""


# frob:doc docs/commands/refactor.md#chunkreport
class ChunkReport(BaseModel):
    """One chunk's outcome: the symbol names it attempted, whether the
    chunk's transaction committed or rolled back, and every verify
    outcome -- `RefactorReport`'s shape at chunk granularity."""

    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...]
    success: bool
    rolled_back: bool
    commit_sha: str | None
    verify_outcomes: tuple[VerifyOutcome, ...]
    aliases: tuple[AliasRecord, ...]
    unresolved: tuple[str, ...]
    error: str | None = None


# frob:doc docs/commands/refactor.md#splitreport
class SplitReport(BaseModel):
    """The whole split's disclosed report: one `ChunkReport` per chunk, in
    the order attempted; `success` is true only when every chunk
    committed."""

    model_config = ConfigDict(frozen=True)

    source_module: str
    destination_module: str
    chunks: tuple[ChunkReport, ...]

    # frob:doc docs/commands/refactor.md#splitreport
    @property
    def success(self) -> bool:
        """True iff every chunk in this split committed -- one failed or
        rolled-back chunk makes the whole split unsuccessful, even though
        earlier chunks' commits are NOT themselves undone (each chunk is
        its own transaction, per the design)."""
        return len(self.chunks) > 0 and all(c.success for c in self.chunks)

    # frob:doc docs/commands/refactor.md#splitreport
    # frob:tests tests/test_refactor.py::TestRunSplit.test_split_moves_symbols_and_leaves_reexport_shim kind="unit"  # noqa: E501
    @property
    def moved_symbols(self) -> tuple[str, ...]:
        """Every symbol name whose own chunk actually committed, in
        order -- exactly the names the source module's re-export shim
        covers."""
        moved: list[str] = []
        for chunk in self.chunks:
            if chunk.success:
                moved.extend(chunk.symbols)
        return tuple(moved)


# frob:doc docs/commands/refactor.md#chunk_symbols
# frob:tests tests/test_refactor.py::TestSplitChunking.test_chunk_symbols_preserves_order_and_size  # noqa: E501
def chunk_symbols(symbols: list[str], chunk_size: int) -> list[list[str]]:
    """Split `symbols` into ordered groups of at most `chunk_size`,
    preserving input order (the design doc's "applies and verifies in
    multiple chunks" requirement, epic acceptance [1])."""
    size = max(1, chunk_size)
    return [symbols[i : i + size] for i in range(0, len(symbols), size)]


# frob:doc docs/commands/refactor.md#build_reexport_shim_op
# frob:tests tests/test_refactor.py::TestSplitReexport.test_shim_op_imports_every_moved_name  # noqa: E501
def build_reexport_shim_op(
    repo_root: Path, source_module: str, destination_module: str, names: list[str]
) -> RewriteOp:
    """One append `RewriteOp` for the source module's file: a `from
    <destination_module> import (name1, name2, ...)  # noqa: F401` block,
    matching the T-1072/T-1077 family-extraction precedent's own re-export
    shape (e.g. `src/frob/gates/__init__.py`'s existing blocks) so external
    `from source import name` call sites never need to change."""
    source_path = module_to_path(repo_root, source_module)
    names_joined = ",\n    ".join(sorted(names))
    text = (
        f"\nfrom {destination_module} import (  # noqa: F401 -- T-1201 split\n"
        f"    {names_joined},\n"
        f")\n"
    )
    return RewriteOp(
        file_path=str(source_path),
        start_line=-1,
        end_line=-1,
        old_text="",
        new_text=text,
        reason=f"re-export shim for symbols split into {destination_module}",
    )


def _import_name_set(new_text: str) -> set[str] | None:
    """The set of imported names in a `from MODULE import a, b, c` rewrite
    string, or `None` if `new_text` does not have that shape. Used only to
    recognize two independently-computed import rewrites as equivalent
    (see `_dedupe_equivalent_import_ops`)."""
    if not new_text.startswith("from ") or " import " not in new_text:
        return None
    _, _, names_part = new_text.partition(" import ")
    return {n.strip() for n in names_part.split(",") if n.strip()}


def _dedupe_equivalent_import_ops(ops: list[RewriteOp]) -> list[RewriteOp]:
    """Two symbols moved out of the SAME source module in the same chunk
    each independently plan a full rewrite of the SAME shared `from
    source import a, b` line (each move's own `scan_references` pass has
    no visibility into its sibling moves in the same chunk) -- both
    rewrites land on the identical resulting name set, just possibly in a
    different order, since each one already lists every sibling name still
    bound at that import alongside its own moved leaf. Collapse any group
    of same-file, same-span ops whose `new_text` all resolve to the SAME
    import-name set (order-insensitive) down to one representative op, so
    `apply_plan`'s overlap guard sees one op per span instead of a false
    conflict; a group whose name sets genuinely differ is left untouched
    (apply_plan's own OverlappingRewrites refusal is the correct outcome
    for a REAL conflict, not this dedup's job to paper over)."""
    by_span: dict[tuple[str, int, int], list[RewriteOp]] = {}
    order: list[tuple[str, int, int]] = []
    for op in ops:
        key = (op.file_path, op.start_line, op.end_line)
        if key not in by_span:
            order.append(key)
        by_span.setdefault(key, []).append(op)

    result: list[RewriteOp] = []
    for key in order:
        group = by_span[key]
        if len(group) == 1 or key[1] == -1:
            result.extend(group)
            continue
        name_sets = [_import_name_set(op.new_text) for op in group]
        resolved_sets = [s for s in name_sets if s is not None]
        if len(resolved_sets) == len(name_sets) and (
            len({frozenset(s) for s in resolved_sets}) == 1
        ):
            _log.info(
                "refactor.split: collapsed %d equivalent import rewrite(s) at %s:%d",
                len(group),
                key[0],
                key[1],
            )
            result.append(group[0])
        else:
            result.extend(group)
    return result


def _plan_chunk(
    repo_root: Path,
    source_module: str,
    destination_module: str,
    symbols: list[str],
    alias_conflict: str,
):
    """Build one merged plan (list of `RewriteOp`, aliases, unresolved,
    resolved-symbol pairs) covering every symbol in this chunk's move plus
    the chunk's own re-export shim -- `Err` on the first symbol that fails
    to plan, before anything in the chunk is written."""
    all_ops: list[RewriteOp] = []
    aliases: list[AliasRecord] = []
    unresolved: list[str] = []
    resolved_pairs = []
    for name in symbols:
        source = SymbolRef(module=source_module, qualname=name)
        destination = SymbolRef(module=destination_module, qualname=name)
        plan_result = build_plan(
            repo_root, RefactorKind.MOVE, source, destination, alias_conflict
        )
        if plan_result.is_err:
            return Err(plan_result.danger_err)
        plan = plan_result.danger_ok
        all_ops.extend(plan.all_ops)
        aliases.extend(plan.aliases)
        unresolved.extend(plan.unresolved)
        resolved_pairs.append((plan.source, destination))
    all_ops = _dedupe_equivalent_import_ops(all_ops)
    shim_op = build_reexport_shim_op(
        repo_root, source_module, destination_module, symbols
    )
    all_ops.append(shim_op)
    return Ok((all_ops, aliases, unresolved, resolved_pairs))


def _run_chunk_verify(
    repo_root: Path,
    touched_files: list[Path],
    run_pytest_collect: bool,
    run_check_delta: bool,
) -> list[VerifyOutcome]:
    """The same three Verify-phase post-conditions `run_refactor` runs per
    single move, run once for a whole chunk's combined touched-file set;
    the pytest-collect and check-delta passes are individually skippable
    exactly as `run_refactor`'s own flags allow (fast local iteration /
    test speed)."""
    outcomes: list[VerifyOutcome] = [
        verify_import_resolution(touched_files, repo_root=repo_root)
    ]
    if run_pytest_collect:
        outcomes.append(verify_pytest_collect(repo_root, targets=touched_files))
    if run_check_delta:
        outcomes.append(verify_check_delta(repo_root))
    return outcomes


def _chunk_failure(
    symbols: list[str],
    error: RefactorError,
    *,
    rolled_back: bool = False,
    aliases: tuple[AliasRecord, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> ChunkReport:
    """One `ChunkReport` shape shared by every early-return failure path in
    `_run_chunk` -- a chunk that never got as far as verify has no verify
    outcomes and no commit, only the `RefactorError` that stopped it."""
    return ChunkReport(
        symbols=tuple(symbols),
        success=False,
        rolled_back=rolled_back,
        commit_sha=None,
        verify_outcomes=(),
        aliases=aliases,
        unresolved=unresolved,
        error=error.value,
    )


def _chunk_preflight(repo_root: Path) -> Result[str, RefactorError]:
    """The two preconditions every chunk needs before planning starts: a
    clean working tree (so a rollback has a real baseline to reset to) and
    the pre-chunk commit sha to reset to. `Ok(pre_sha)` on success."""
    clean_result = working_tree_clean(repo_root)
    if clean_result.is_err or not clean_result.danger_ok:
        return Err(RefactorError.DirtyWorkingTree)
    sha_result = current_sha(repo_root)
    if sha_result.is_err:
        return Err(RefactorError.GitError)
    return Ok(sha_result.danger_ok)


def _apply_chunk(
    repo_root: Path,
    all_ops: list[RewriteOp],
    aliases: list[AliasRecord],
    unresolved: list[str],
    resolved_pairs: list,
) -> Result[None, RefactorError]:
    """Build the chunk's merged `RefactorPlan` and hand it to `apply_plan`,
    cleaning up any partially-written files on refusal. On success, carries
    each moved symbol's lock acks forward (T-1201's per-symbol carry step)
    -- the working tree is left dirty-but-applied for the caller to `git
    add`/commit."""
    # A chunk moves several symbols at once, so there is no single
    # `RefactorPlan.source`/`destination` the way a lone move/rename has
    # one -- `apply_plan` only ever reads `.all_ops`, so this plan's own
    # `move_ops` is left empty and every op (moves plus references plus
    # the shim) travels through `reference_ops` instead. `source`/
    # `destination` are filled with the chunk's first symbol purely to
    # satisfy the model's required fields; nothing reads them here.
    chunk_plan = RefactorPlan(
        kind=RefactorKind.MOVE,
        source=resolved_pairs[0][0],
        destination=resolved_pairs[0][1],
        move_ops=(),
        reference_ops=tuple(all_ops),
        aliases=tuple(aliases),
        unresolved=tuple(unresolved),
    )
    apply_result = apply_plan(repo_root, chunk_plan)
    if apply_result.is_err:
        git(repo_root, "checkout", "--", ".")
        touched = {op.file_path for op in all_ops}
        git(repo_root, "clean", "-fd", "--", *touched)
        return Err(apply_result.danger_err)

    for source, destination in resolved_pairs:
        carry_lock_acks(repo_root, source, destination)
    return Ok(None)


def _commit_chunk(
    repo_root: Path,
    source_module: str,
    destination_module: str,
    symbols: list[str],
    pre_sha: str,
) -> Result[str, RefactorError]:
    """`git add -A` plus one commit for an already-applied chunk, resetting
    all the way back to `pre_sha` (undoing the apply too) on either git
    step's failure. `Ok(commit_sha)` on success."""
    add_result = git(repo_root, "add", "-A")
    if add_result.is_err or add_result.danger_ok.returncode != 0:
        git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    commit_msg = (
        f"wip(refactor): split {source_module} -> {destination_module} "
        f"({', '.join(symbols)})"
    )
    commit_result = git(repo_root, "commit", "-m", commit_msg)
    if commit_result.is_err or commit_result.danger_ok.returncode != 0:
        git(repo_root, "reset", "--hard", pre_sha)
        return Err(RefactorError.GitError)
    commit_sha = current_sha(repo_root)
    return Ok(commit_sha.danger_ok if commit_sha.is_ok else "")


def _verify_or_rollback_chunk(
    repo_root: Path,
    all_ops: list[RewriteOp],
    pre_sha: str,
    run_pytest_collect: bool,
    run_check_delta: bool,
) -> tuple[list[VerifyOutcome], bool, bool]:
    """Run the chunk's verify outcomes and, if any failed, reset back to
    `pre_sha` (undoing the commit). Returns `(outcomes, success,
    rolled_back)`."""
    touched_files = sorted({Path(op.file_path) for op in all_ops})
    outcomes = _run_chunk_verify(
        repo_root, touched_files, run_pytest_collect, run_check_delta
    )
    success = all(outcome.passed for outcome in outcomes)
    rolled_back = False
    if not success:
        _log.warning("refactor.split: chunk verify failed, rolling back to %s", pre_sha)
        reset_result = git(repo_root, "reset", "--hard", pre_sha)
        rolled_back = reset_result.is_ok and reset_result.danger_ok.returncode == 0
    return outcomes, success, rolled_back


def _run_chunk(
    repo_root: Path,
    source_module: str,
    destination_module: str,
    symbols: list[str],
    alias_conflict: str,
    run_pytest_collect: bool = True,
    run_check_delta: bool = True,
) -> ChunkReport:
    """Plan, apply, verify, and commit-or-rollback exactly one chunk as a
    single transaction -- mirrors `run_refactor`'s own single-symbol
    pipeline, at chunk granularity."""
    preflight_result = _chunk_preflight(repo_root)
    if preflight_result.is_err:
        return _chunk_failure(symbols, preflight_result.danger_err)
    pre_sha = preflight_result.danger_ok

    plan_result = _plan_chunk(
        repo_root, source_module, destination_module, symbols, alias_conflict
    )
    if plan_result.is_err:
        return _chunk_failure(symbols, plan_result.danger_err)
    all_ops, aliases, unresolved, resolved_pairs = plan_result.danger_ok

    apply_result = _apply_chunk(repo_root, all_ops, aliases, unresolved, resolved_pairs)
    if apply_result.is_err:
        return _chunk_failure(
            symbols,
            apply_result.danger_err,
            aliases=tuple(aliases),
            unresolved=tuple(unresolved),
        )

    commit_result = _commit_chunk(
        repo_root, source_module, destination_module, symbols, pre_sha
    )
    if commit_result.is_err:
        return _chunk_failure(
            symbols,
            commit_result.danger_err,
            rolled_back=True,
            aliases=tuple(aliases),
            unresolved=tuple(unresolved),
        )
    commit_sha_val = commit_result.danger_ok or None

    outcomes, success, rolled_back = _verify_or_rollback_chunk(
        repo_root, all_ops, pre_sha, run_pytest_collect, run_check_delta
    )

    return ChunkReport(
        symbols=tuple(symbols),
        success=success,
        rolled_back=rolled_back,
        commit_sha=None if rolled_back else commit_sha_val,
        verify_outcomes=tuple(outcomes),
        aliases=tuple(aliases),
        unresolved=tuple(unresolved),
        error=None,
    )


# frob:doc docs/commands/refactor.md#run_split
# frob:tests tests/test_refactor.py::TestRunSplit.test_split_moves_symbols_and_leaves_reexport_shim  # noqa: E501
# frob:tests tests/test_refactor.py::TestRunSplit.test_split_chunk_failure_does_not_touch_later_chunks  # noqa: E501
def run_split(
    repo_root: Path,
    source_module: str,
    symbols: list[str],
    destination_module: str,
    alias_conflict: str = "error",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    run_pytest_collect: bool = True,
    run_check_delta: bool = True,
) -> Result[SplitReport, RefactorError]:
    """The whole split pipeline: chunk `symbols`, then plan/apply/verify/
    commit-or-rollback each chunk in order as its OWN transaction. Stops
    attempting further chunks the moment one fails (an already-committed
    earlier chunk is left in place, per the design doc's per-chunk
    transaction model) and returns `Ok(SplitReport)` either way -- `Err`
    only for a precondition that refuses before any chunk starts (empty
    symbol list, dirty tree at the very start)."""
    if not symbols:
        return Err(RefactorError.TargetNotFound)
    clean_result = working_tree_clean(repo_root)
    if clean_result.is_err:
        return Err(clean_result.danger_err)
    if not clean_result.danger_ok:
        return Err(RefactorError.DirtyWorkingTree)

    chunks: list[ChunkReport] = []
    for group in chunk_symbols(symbols, chunk_size):
        chunk_report = _run_chunk(
            repo_root,
            source_module,
            destination_module,
            group,
            alias_conflict,
            run_pytest_collect=run_pytest_collect,
            run_check_delta=run_check_delta,
        )
        chunks.append(chunk_report)
        _log.info(
            "refactor.split: chunk %s success=%s rolled_back=%s",
            group,
            chunk_report.success,
            chunk_report.rolled_back,
        )
        if not chunk_report.success:
            _log.warning(
                "refactor.split: stopping after failed chunk %s, "
                "%d chunk(s) not attempted",
                group,
                len(chunk_symbols(symbols, chunk_size)) - len(chunks),
            )
            break

    return Ok(
        SplitReport(
            source_module=source_module,
            destination_module=destination_module,
            chunks=tuple(chunks),
        )
    )
