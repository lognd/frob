"""frob.mutate -- mutation testing, the honest test-quality oracle (T-0011).

Coverage and case-counts are gameable (an assert-free test passes them);
mutation testing is not. It perturbs a function's source with small
semantic mutations (flip a comparison, swap an operator, negate a boolean,
mutate a return), runs the tests bound to that function, and reports which
mutants SURVIVED -- a survivor is a behavior change no test noticed, i.e. a
real gap. The mutation score (killed / total) is the quality signal the
TEST gates' counts only approximate.

v1 mutates Python source via a small AST transformer and runs the
touched-set tests through frob.testing; other languages are recorded work.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.mutate._journal import (
    JournalError,
    StaleJournal,
    record_journal_progress,
    remove_journal,
    restore_stale_journals,
    write_journal,
)
from frob.process._lock import derived_state_lock

_log = get_logger(__name__)

# frob:doc docs/modules/mutate.md#public-api
# Set to "1" in the environment of every test process `_run_mutants` spawns.
# Recursion guard (T-0755): an evidence test that itself invokes the
# mutation harness against the real repo (the TEST016 self-check) MUST skip
# when it sees this sentinel, or each mutant run re-enters the harness and
# the suite becomes a self-sustaining fork bomb.
MUTATION_RUN_ENV = "FROB_MUTATION_RUN"

# (from-op, to-op) mutations, applied one at a time.
_COMPARE_SWAPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Lt: ast.GtE,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.GtE: ast.Lt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}
_BINOP_SWAPS: dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.Div: ast.Mult,
}
_BOOLOP_SWAPS: dict[type[ast.boolop], type[ast.boolop]] = {
    ast.And: ast.Or,
    ast.Or: ast.And,
}


# frob:doc docs/modules/mutate.md#public-api
class MutateError(ErrorSet):
    """Fallible outcomes of mutation testing."""

    ParseFailed = "Source file could not be parsed"
    NoSource = "Target file does not exist"
    ExecDisabled = (
        "exec capability disabled via kill switch -- mutation run aborted, no score"
    )
    JournalCollision = (
        "a mutate-backup journal for this file already exists with different "
        "content -- a concurrent mutation run may be active, or a crash left "
        "a journal `frob doctor` should be consulted for (T-0857)"
    )


# frob:doc docs/modules/mutate.md#public-api
class Mutant(BaseModel):
    """One applied mutation: what changed and where."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    description: str


# frob:doc docs/modules/mutate.md#public-api
class MutationResult(BaseModel):
    """The outcome of testing one function's mutants."""

    model_config = ConfigDict(frozen=True)

    total: int
    killed: int
    survivors: tuple[Mutant, ...]

    @property
    def score(self) -> float:
        """Killed / total (1.0 = every mutant caught; NaN-safe as 1.0)."""
        # frob:doc docs/modules/mutate.md#public-api
        return 1.0 if self.total == 0 else self.killed / self.total


@dataclass
class _Mutation:
    """An in-flight mutation: the transformed source and its description."""

    source: str
    mutant: Mutant


# frob:ticket T-1038
class _Mutator(ast.NodeTransformer):
    """Applies exactly ONE mutation, identified by a running counter."""

    def __init__(self, target_index: int) -> None:
        self._target = target_index
        self._seen = 0
        self.applied: str | None = None
        # T-0755 reviewer round 2: the mutated NODE's own lineno, not the
        # whole file's -- `_mutation_at` used to report the first lineno of
        # the ENTIRE reparsed tree (effectively always line 1), which made
        # every `Mutant.line` wrong for any mutation past the first
        # statement. Set at the exact `_hit` that fires.
        self.hit_line = 0

    def _hit(self, desc: str, lineno: int) -> bool:
        current = self._seen
        self._seen += 1
        if current == self._target:
            self.applied = desc
            self.hit_line = lineno
            return True
        return False

    def visit_Compare(self, node: ast.Compare):  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in _COMPARE_SWAPS:
            if self._hit(f"compare {type(node.ops[0]).__name__} swapped", node.lineno):
                node.ops = [_COMPARE_SWAPS[type(node.ops[0])]()]
        return node

    # frob:ticket T-1038
    # frob:waive AFFECT001 reason="T-1038: OPAQUE001 hardening -- added a reasoned \
    # frob:waive comment above the existing type(node.op) dynamic-key call; the \
    # documented single-mutation-per-call contract and behavior are unchanged, nothing \
    # for docs/modules/mutate.md#public-api to update"
    def visit_BinOp(self, node: ast.BinOp):  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        self.generic_visit(node)
        # frob:waive OPAQUE001 reason="T-1038: type(node.op) is checked against \
        # _BINOP_SWAPS's own key set (the 'in' test immediately above) before the \
        # dynamic-key call -- an ast.operator subclass, never attacker/external input"
        if type(node.op) in _BINOP_SWAPS and self._hit(
            f"binop {type(node.op).__name__} swapped", node.lineno
        ):
            node.op = _BINOP_SWAPS[type(node.op)]()
        return node

    # frob:ticket T-1038
    # frob:waive AFFECT001 reason="T-1038: OPAQUE001 hardening -- added a reasoned \
    # frob:waive comment above the existing type(node.op) dynamic-key call; the \
    # documented single-mutation-per-call contract and behavior are unchanged, nothing \
    # for docs/modules/mutate.md#public-api to update"
    def visit_BoolOp(self, node: ast.BoolOp):  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        self.generic_visit(node)
        # frob:waive OPAQUE001 reason="T-1038: type(node.op) is checked against \
        # _BOOLOP_SWAPS's own key set (the 'in' test immediately above) before the \
        # dynamic-key call -- an ast.boolop subclass, never attacker/external input"
        if type(node.op) in _BOOLOP_SWAPS and self._hit(
            f"boolop {type(node.op).__name__} swapped", node.lineno
        ):
            node.op = _BOOLOP_SWAPS[type(node.op)]()
        return node

    def visit_Constant(self, node: ast.Constant):  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        if isinstance(node.value, bool) and self._hit(
            f"bool {node.value} negated", node.lineno
        ):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node


def _count_mutations(tree: ast.AST) -> int:
    """How many single-point mutations the source admits."""
    counter = _Mutator(-1)  # never hits; just counts via _seen
    counter.visit(tree)
    return counter._seen


class _PointCollector(ast.NodeVisitor):
    """Records each mutation point's `(index, lineno)` in the SAME order
    `_Mutator` numbers them (T-0755 reviewer fix), without mutating
    anything -- lets a caller (`generate_mutants`' `line_ranges` filter)
    know which point indices fall inside a diff's changed lines BEFORE
    spending a subprocess on any of them. Mirrors `_Mutator`'s exact
    visit_X methods and post-order (`generic_visit` first, then check the
    node itself) so index N here always means the same point index N
    `_Mutator(N)` would apply."""

    def __init__(self) -> None:
        self._seen = 0
        self.points: list[tuple[int, int]] = []

    def _record(self, node: ast.AST) -> None:
        lineno = getattr(node, "lineno", 0)
        self.points.append((self._seen, lineno))
        self._seen += 1

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        # frob:tests tests/test_mutate.py::test_point_collector_indexing_matches_mutator kind="unit"  # noqa: E501
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in _COMPARE_SWAPS:
            self._record(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        # frob:tests tests/test_mutate.py::test_point_collector_indexing_matches_mutator kind="unit"  # noqa: E501
        self.generic_visit(node)
        if type(node.op) in _BINOP_SWAPS:
            self._record(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        # frob:tests tests/test_mutate.py::test_point_collector_indexing_matches_mutator kind="unit"  # noqa: E501
        self.generic_visit(node)
        if type(node.op) in _BOOLOP_SWAPS:
            self._record(node)

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        # frob:doc docs/modules/mutate.md#public-api
        # frob:tests tests/test_mutate.py::test_point_collector_indexing_matches_mutator kind="unit"  # noqa: E501
        if isinstance(node.value, bool):
            self._record(node)


def _mutation_point_linenos(tree: ast.AST) -> tuple[int, ...]:
    """Every mutation point's line number, indexed identically to
    `_Mutator`'s own numbering (T-0755) -- `result[i]` is the line
    `_Mutator(i)` would mutate."""
    collector = _PointCollector()
    collector.visit(tree)
    return tuple(lineno for _, lineno in collector.points)


def _in_any_range(lineno: int, line_ranges: tuple[tuple[int, int], ...]) -> bool:
    """Whether `lineno` falls inside at least one inclusive `(start, end)`
    span of `line_ranges` (T-0755's diff-scoping filter)."""
    return any(start <= lineno <= end for start, end in line_ranges)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _Mutator.visit (a custom \
# ast.NodeVisitor subclass whose per-node-type visit_* methods the resolver cannot \
# enumerate) and ast.unparse/ast.fix_missing_locations, stdlib ast calls over an \
# already-caught ast.parse tree; no further raise path is reachable from this \
# function's own locally-visible calls"
def _mutation_at(
    source: str, i: int, file: str
) -> Result[_Mutation | None, MutateError]:
    """Apply single-point mutation `i` to a fresh parse of `source`;
    `Ok(None)` if mutation point `i` doesn't apply."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return Err(MutateError.ParseFailed)
    mutator = _Mutator(i)
    mutator.visit(tree)
    applied = mutator.applied
    if applied is None:
        return Ok(None)
    ast.fix_missing_locations(tree)
    return Ok(
        _Mutation(
            source=ast.unparse(tree),
            mutant=Mutant(file=file, line=mutator.hit_line, description=str(applied)),
        )
    )


# frob:doc docs/modules/mutate.md#public-api
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _count_mutations/ \
# _mutation_point_linenos (custom ast.NodeVisitor walks the resolver cannot enumerate) \
# and _mutation_at's own already-Result-wrapped call below; the one real raise path \
# (ast.parse) is caught above"
def generate_mutants(
    source: str,
    file: str,
    line_ranges: tuple[tuple[int, int], ...] | None = None,
) -> Result[tuple[_Mutation, ...], MutateError]:
    """Every single-point mutation of `source` as (mutated_source, Mutant).

    T-0755 reviewer fix: `line_ranges` (default `None`, unbounded, every
    caller before this ticket unaffected), when given, restricts the
    result to points whose line falls inside at least one inclusive
    `(start, end)` span -- diff-scoped mutation testing needs to mutate
    ONLY the changed lines of a file, not "whatever else happens to live
    in the same file" (a file-wide point selection previously let an
    unrelated pre-existing line supply every mutant for a 2-line diff, the
    exact false-positive the reviewer reproduced on this ticket's own
    diff)."""
    try:
        base = ast.parse(source)
    except SyntaxError:
        return Err(MutateError.ParseFailed)
    total = _count_mutations(base)
    if line_ranges is not None:
        linenos = _mutation_point_linenos(base)
        allowed = {
            i for i, lineno in enumerate(linenos) if _in_any_range(lineno, line_ranges)
        }
    else:
        allowed = None
    mutations: list[_Mutation] = []
    for i in range(total):
        if allowed is not None and i not in allowed:
            continue
        result = _mutation_at(source, i, file)
        if result.is_err:
            return Err(result.danger_err)
        mutation = result.danger_ok
        if mutation is not None:
            mutations.append(mutation)
    return Ok(tuple(mutations))


# frob:doc docs/modules/mutate.md#public-api
# frob:invariant INV-017
# invariant spec: [INV-017](invariants/INV-017.md)
def run_mutations(
    root: Path,
    file: Path,
    test_argv: tuple[str, ...],
    timeout_s: float = 300.0,
    max_mutants: int | None = None,
    line_ranges: tuple[tuple[int, int], ...] | None = None,
    deadline_monotonic: float | None = None,
) -> Result[MutationResult, MutateError]:
    """Mutate `file` one point at a time; a mutant is KILLED if `test_argv`
    fails against it, SURVIVED if the tests still pass.

    The file is restored after every mutant (and on any error) via a
    `finally`. That alone does not survive a KILLED process (a SIGKILL, an
    OOM kill, the T-0755 fork-bomb scenario never reaches the `finally`) --
    T-0857 closes that gap: before the first mutant write, the target's
    pre-mutation bytes are journaled to `.frob/mutate-backup/`
    (`frob.mutate._journal.write_journal`) and removed only after a
    successful restore, so a crashed run always leaves a recoverable
    original on disk instead of the mutant. Every call also restores any
    STALE journal left by a PRIOR crashed run before doing anything else
    (`restore_stale_journals`, logged loudly at WARNING) -- `frob doctor`
    surfaces the same state read-only via `list_stale_journals`.

    T-0755: `max_mutants` (default `None`, unbounded, preserving every
    caller before this ticket) caps how many of `generate_mutants`' points
    are actually spawned against -- a bound the diff-scoped evidence
    obligation needs to stay cheap (one mutant is one full test-command
    subprocess, and a hot file can admit dozens of points). Capping takes
    the FIRST `max_mutants` points in source order, not a random sample, so
    a run is deterministic and reproducible run-to-run.

    `line_ranges` (T-0755 reviewer fix, default `None`, unbounded) is
    forwarded straight to `generate_mutants` -- see its docstring. Applied
    BEFORE `max_mutants` truncates, so a diff-scoped caller's cap counts
    only points that actually fall inside the changed lines.

    T-0879: holds `derived_state_lock(root, exclusive=True)` for the whole
    run -- `run_mutations` is a `.frob`-derived-state writer (the journal
    under `.frob/mutate-backup/`) in the same sense `frob doctor`'s
    manifest write is, and is always invoked standalone (`frob mutate`,
    `frob ticket close/land`'s mutation-evidence obligation) rather than
    nested inside an already-locked `frob check` run, so taking the
    EXCLUSIVE lock here cannot self-deadlock against a SHARED holder in
    the same process. See `derived_state_lock`'s docstring for the
    shared/exclusive contract.

    `deadline_monotonic` (T-1727, default `None`, unbounded, preserving
    every caller before this ticket): an absolute `time.monotonic()`
    deadline shared across a WHOLE multi-file sweep (the caller computes
    it once, not per-file), checked by `_run_mutants` before starting
    each mutant. When the deadline is already past, remaining mutants in
    THIS file are skipped -- `MutationResult.killed + len(survivors) <
    MutationResult.total` is how a caller detects this happened (no
    separate flag: the arithmetic already says "fewer were attempted than
    were planned"). This is a genuinely UNMEASURED remainder, never
    silently folded into "survived": a mutant nobody ran proves nothing
    either way, so the caller must not read a truncated run's low kill
    count as if it were a real confirmatory-only verdict (T-1727,
    mirroring T-1703's "could not measure must never render as
    verified").
    """
    target = root / file if not file.is_absolute() else file
    if not target.exists():
        return Err(MutateError.NoSource)
    with derived_state_lock(root, exclusive=True):
        _restore_any_stale_journals(root)
        original_bytes = target.read_bytes()
        prepared = _prepare_mutants(original_bytes, file, line_ranges, max_mutants)
        if prepared.is_err:
            return Err(prepared.danger_err)
        mutants = prepared.danger_ok
        journaled = write_journal(root, target, original_bytes)
        if journaled.is_err:
            _log.error(
                "mutate: aborting run for %s -- journal collision (%s)",
                target,
                journaled.danger_err,
            )
            return Err(MutateError.JournalCollision)
        try:
            run_result = _run_mutants(
                target,
                mutants,
                test_argv,
                root,
                timeout_s,
                deadline_monotonic=deadline_monotonic,
            )
        finally:
            # Only drop the journal once the restore write has actually
            # succeeded (T-0857) -- if `write_bytes` itself raises (a disk
            # error mid-restore), the journal must survive so the NEXT
            # `run_mutations` call's `restore_stale_journals` can still fix it.
            target.write_bytes(original_bytes)
            remove_journal(root, target)
        if run_result.is_err:
            _log.error(
                "mutate: run aborted (%s) -- no mutation score, not a false 100%%",
                run_result.danger_err,
            )
            return Err(run_result.danger_err)
        killed, survivors = run_result.danger_ok
        _log.info(
            "mutate: %d mutant(s), %d killed, %d survived",
            len(mutants),
            killed,
            len(survivors),
        )
    return Ok(
        MutationResult(total=len(mutants), killed=killed, survivors=tuple(survivors))
    )


# frob:ticket T-0976
def _restore_any_stale_journals(root: Path) -> None:
    """Restore (and loudly warn about) any `.frob/mutate-backup/` journal
    left by a prior crashed `run_mutations` call before this one starts --
    the T-0857 recovery half of `run_mutations`, split from its own main
    body."""
    restored = restore_stale_journals(root)
    if restored:
        _log.warning(
            "mutate: restored %d stale journal(s) left by a prior crashed run "
            "before starting: %s",
            len(restored),
            restored,
        )


# frob:ticket T-0976
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to generate_mutants's own internal \
# call graph (ast NodeVisitor walks the resolver cannot enumerate), already wrapped as \
# a typani Result and checked via .is_err below; the only locally-visible fallible \
# step (bytes.decode) is caught above"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def _prepare_mutants(
    original_bytes: bytes,
    file: Path,
    line_ranges: tuple[tuple[int, int], ...] | None,
    max_mutants: int | None,
) -> Result[tuple["_Mutation", ...], MutateError]:
    """Decode `original_bytes` and run `generate_mutants` over it, capped
    to `max_mutants` (T-0755, first-`max_mutants`-in-source-order,
    deterministic) -- the mutant-generation half of `run_mutations`, split
    from its journal/subprocess-running half."""
    try:
        original = original_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return Err(MutateError.ParseFailed)
    generated = generate_mutants(original, str(file), line_ranges)
    if generated.is_err:
        return Err(generated.danger_err)
    mutants = generated.danger_ok
    if max_mutants is not None:
        mutants = mutants[:max_mutants]
    return Ok(mutants)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to guarded_subprocess_run, a \
# cross-module Result-returning wrapper the resolver cannot see through; every one of \
# its documented raise paths is caught in this function's per-mutation try block below"
def _run_mutants(
    target: Path,
    mutants: tuple[_Mutation, ...],
    test_argv: tuple[str, ...],
    root: Path,
    timeout_s: float,
    *,
    deadline_monotonic: float | None = None,
) -> Result[tuple[int, list[Mutant]], MutateError]:
    """Write and test each mutant in turn: `(killed_count, surviving_mutants)`.

    Caller is responsible for restoring `target`'s original content afterward.

    T-0803 reviewer fix: a refused spawn (`FROB_DISABLE_EXEC=1`) is NOT
    scored as "killed" -- unlike a `TimeoutExpired` hang (real, OBSERVED
    behavior under the mutant), a refusal ran nothing at all, so treating
    it as a kill would produce a fabricated 100% mutation score / zero
    survivors under the kill switch, an env-var-gameable rubber stamp on
    a suite that was never actually exercised. Instead this aborts the
    whole run with `Err(MutateError.ExecDisabled)` on the FIRST refusal --
    mirroring the honest `Err`/`raise` semantics `_coverage_wait.py`/
    `_vm_runner.py` already chose for the same kill-switch case.

    T-1727: `deadline_monotonic`, checked before EACH mutant (not just at
    entry), stops the loop early once `time.monotonic()` passes it --
    `killed + len(survivors)` then comes back short of `len(mutants)`,
    the caller's signal that the remainder is UNMEASURED, not survived.
    Logs one INFO line per mutant attempted (`mutant N/M`) so a long
    sweep is visibly progressing rather than indistinguishable from a
    hang (T-1727 requirement 3) -- the whole reason this ticket exists is
    ten consecutive silent 540s timeouts that gave no signal either way.
    """
    import os
    import subprocess
    import time

    from frob.process._guard import guarded_subprocess_run

    child_env = {**os.environ, MUTATION_RUN_ENV: "1"}
    killed = 0
    survivors: list[Mutant] = []
    total = len(mutants)
    for index, mutation in enumerate(mutants, start=1):
        if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
            _log.warning(
                "mutate: sweep budget exceeded before mutant %d/%d of %s -- "
                "stopping early, %d mutant(s) UNMEASURED (not killed, not survived)",
                index,
                total,
                target,
                total - (index - 1),
            )
            break
        _log.info(
            "mutate: mutant %d/%d of %s (line %d, %s)",
            index,
            total,
            target,
            mutation.mutant.line,
            mutation.mutant.description,
        )
        target.write_text(mutation.source, encoding="utf-8")
        # T-1327: keep the journal's "last known on-disk content" hash in
        # step with what was actually just written, so a crash mid-mutant
        # leaves a journal a LATER restore can verify against (rather
        # than trusting the writer-dead check alone -- see
        # frob.mutate._journal's stale-restore verification section).
        record_journal_progress(root, target, mutation.source.encode("utf-8"))
        try:
            guarded = guarded_subprocess_run(
                list(test_argv),
                cwd=root,
                capture_output=True,
                timeout=timeout_s,
                env=child_env,
            )
        except subprocess.TimeoutExpired:
            killed += 1  # a mutant that hangs the tests is caught
            continue
        if guarded.is_err:
            _log.warning(
                "mutate: test spawn refused (exec disabled) for mutant %s -- "
                "aborting run, not scoring as killed",
                mutation.mutant.description,
            )
            return Err(MutateError.ExecDisabled)
        proc = guarded.danger_ok
        if proc.returncode != 0:
            killed += 1
        else:
            _log.info("mutate: SURVIVOR %s", mutation.mutant.description)
            survivors.append(mutation.mutant)
    return Ok((killed, survivors))


__all__ = [
    "JournalError",
    "MUTATION_RUN_ENV",
    "Mutant",
    "MutateError",
    "MutationResult",
    "StaleJournal",
    "generate_mutants",
    "run_mutations",
]
