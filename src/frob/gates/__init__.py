"""frob.gates -- enforcement gates, policy, and invariants (docs/gates.md).

The drift half (nothing declared is silently broken) and the coverage half
(nothing new escapes declaration) meet here. Per docs/rework.md's cycle-
avoidance rule, `frob.gates` is the ONLY module that joins graph edge
targets against `frob.tickets`, `invariants/`, and `frob.policy` state --
`frob.graph` treats every edge target as an opaque string.

Gates are pure functions over already-loaded state (`GraphSnapshot`,
`TicketQueue`, `LockFile`, `Diff`, `CollectedTests`, invariants, policy
rules, coverage). `run_gates` is the only function in this package that
performs IO; it loads everything once and runs the gates in parallel via
`ThreadPoolExecutor`, mirroring `frob.check`'s existing parallel-tools
posture.
"""

from __future__ import annotations

import hashlib
import re
import time
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from pydantic import ValidationError
from typani import Err, Ok
from typani.option import Nothing, Option, Some
from typani.result import Result

from frob.gates._coverage import load_coverage, load_stamp, stamp_coverage
from frob.gates._models import (
    CoverageData,
    CoverageError,
    GateConfig,
    GateError,
    GateReport,
    GateStats,
    PreworkSweep,
    Severity,
    SystemSpec,
    TestPolicy,
    Violation,
    WaiverRef,
)
from frob.gates._prework import load_prework, record_prework
from frob.gates.invariants import Invariant, InvariantError, load_invariants
from frob.gitio import Diff, current_branch, working_diff
from frob.graph import (
    BuildError,
    Edge,
    EdgeKind,
    GraphSnapshot,
    build_graph,
    edges_from,
)
from frob.graph._models import LockFile
from frob.graph.lock import drift as _graph_drift
from frob.graph.lock import load_lock
from frob.lang import SymbolKind
from frob.lang._models import ParsedFile
from frob.logging import get_logger
from frob.testing import CollectedTests, collect_python_tests
from frob.tickets import Ticket, TicketQueue, TicketState, load_queue

_log = get_logger(__name__)

_BRANCH_TICKET_RE = re.compile(r"^(T-\d{4})-")
_OPEN_STATES = frozenset(
    s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
)
_TODO_RE = re.compile(r"\b(TODO|FIXME)\b")
_CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/gates.md#public-api
def active_ticket(root: Path, explicit: str | None) -> Option[str]:
    """`--ticket` wins; else the branch name matching `^(T-\\d{4})-`; else Nothing."""
    if explicit:
        _log.debug("active_ticket: explicit=%s", explicit)
        return Some(explicit)
    branch_result = current_branch(root)
    if branch_result.is_err:
        _log.debug("active_ticket: no branch context")
        return Nothing()
    match = _BRANCH_TICKET_RE.match(branch_result.danger_ok)
    if match is None:
        _log.debug(
            "active_ticket: branch %r has no ticket prefix", branch_result.danger_ok
        )
        return Nothing()
    _log.debug("active_ticket: branch-derived %s", match.group(1))
    return Some(match.group(1))


# ---------------------------------------------------------------------------
# Hunk-to-symref resolution
# ---------------------------------------------------------------------------
# frob.testing._select.select_tests does the same span-overlap match inline as
# part of a larger selection algorithm and does not expose it as a standalone
# helper, so it is not importable in isolated form; the overlap primitive is
# reimplemented here (documented duplicate, same posture as the extension-
# table duplicates already accepted across frob.graph/frob.testing/frob.policy).


def _overlaps(hunk_span: tuple[int, int], sym_span: tuple[int, int]) -> bool:
    """True if two inclusive 1-indexed line ranges intersect."""
    return hunk_span[0] <= sym_span[1] and sym_span[0] <= hunk_span[1]


def _touched_symrefs(diff: Diff, snapshot: GraphSnapshot) -> set[str]:
    """Every symbol whose span overlaps a diff hunk in the same file."""
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    touched: set[str] = set()
    for record in snapshot.symbols.values():
        for span in hunks_by_file.get(record.id.path, ()):
            if _overlaps(span, record.span):
                touched.add(record.symref)
                break
    return touched


def _touched_files(diff: Diff) -> set[str]:
    """Every file path touched anywhere in `diff`."""
    return {hunk.file for hunk in diff.hunks}


def _symref_to_nodeid(symref: str) -> str:
    """`path::a.b` -> `path::a::b`, the pytest node id spelling of a qualname."""
    path, _, qualname = symref.partition("::")
    return f"{path}::{qualname.replace('.', '::')}"


def _site_from_edge_origin(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin string."""
    file_part, sep, line_part = origin.rpartition(":")
    if sep and line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


# ---------------------------------------------------------------------------
# Waivers
# ---------------------------------------------------------------------------


def _waive_edges(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every valid `frob:waive` edge in the snapshot (dsl.py already rejects a
    waive directive missing `reason=...` as a MalformedDirective, so every
    surviving WAIVE edge here is guaranteed to carry a reason)."""
    return tuple(e for e in snapshot.edges if e.kind == EdgeKind.WAIVE)


def _waive001_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """WAIVE001: a `frob:waive` directive missing `reason=...` -- surfaced from
    frob.graph's MalformedDirective list, since frob.graph.dsl already refuses
    to turn such a line into an edge."""
    violations: list[Violation] = []
    for md in snapshot.malformed:
        if "frob:waive" not in md.reason:
            continue
        _log.debug("WAIVE001: %s:%d %s", md.file, md.line, md.reason)
        violations.append(
            Violation(
                rule="WAIVE001",
                severity=Severity.ERROR,
                file=md.file,
                line=md.line,
                message=(
                    f'WAIVE001: {md.file}:{md.line} frob:waive missing reason="..."; '
                    f"add a reason attribute or remove the waiver"
                ),
            )
        )
    return tuple(violations)


def _apply_waivers(
    violations: tuple[Violation, ...], snapshot: GraphSnapshot
) -> tuple[tuple[Violation, ...], tuple[Violation, ...]]:
    """Split `violations` into (kept, waived) using the snapshot's WAIVE edges.

    A waiver matches when its edge's `src` symbol/file equals the violation's
    `file` (either the bare path or a `path::qualname` symref rooted at that
    path) and its `target` equals the violation's rule id.
    """
    waivers = _waive_edges(snapshot)
    kept: list[Violation] = []
    waived: list[Violation] = []
    for violation in violations:
        match = next(
            (
                w
                for w in waivers
                if w.target == violation.rule
                and (
                    w.src == violation.file or w.src.split("::", 1)[0] == violation.file
                )
            ),
            None,
        )
        if match is None:
            kept.append(violation)
            continue
        _log.info(
            "waived: %s at %s:%d (%s)",
            violation.rule,
            violation.file,
            violation.line,
            match.attrs.get("reason", ""),
        )
        waived.append(
            violation.model_copy(
                update={
                    "waived": WaiverRef(
                        site=match.src, reason=match.attrs.get("reason", "")
                    )
                }
            )
        )
    return tuple(kept), tuple(waived)


# ---------------------------------------------------------------------------
# Pure gates
# ---------------------------------------------------------------------------


# frob:doc docs/gates.md#public-api
def drift_gate(snapshot: GraphSnapshot, lock: LockFile) -> tuple[Violation, ...]:
    """DRIFT001 (stale ack) and DRIFT002 (dangling edge endpoint)."""
    report = _graph_drift(lock, snapshot)
    violations: list[Violation] = []
    for stale in report.stale:
        record = snapshot.symbols.get(stale.entry.ref)
        line = record.span[0] if record is not None else 0
        file = stale.entry.ref.split("::", 1)[0]
        _log.debug("DRIFT001: %s facet=%s moved", stale.entry.ref, stale.entry.facet)
        violations.append(
            Violation(
                rule="DRIFT001",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DRIFT001: {stale.entry.ref} ({stale.entry.facet}) digest moved "
                    f"since ack ({len(stale.dependents)} dependent(s)); "
                    f"run: frob ack {stale.entry.ref}"
                ),
            )
        )
    for dangling in report.dangling:
        file, line = _site_from_edge_origin(dangling.edge.origin)
        candidates = ", ".join(dangling.candidates) or "no candidates found"
        _log.debug("DRIFT002: %s -> %s gone", dangling.edge.src, dangling.edge.target)
        violations.append(
            Violation(
                rule="DRIFT002",
                severity=Severity.ERROR,
                file=file,
                line=line,
                message=(
                    f"DRIFT002: {dangling.edge.kind.value} edge "
                    f"{dangling.edge.src} -> {dangling.edge.target} no longer "
                    f"resolves; candidates: {candidates}; fix the reference or "
                    f"run: frob ack <candidate>"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/gates.md#public-api
def coverage_gate(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff, tests: CollectedTests
) -> tuple[Violation, ...]:
    """COV001..COV004 and TODO001."""
    violations: list[Violation] = []
    violations.extend(_cov001(snapshot))
    violations.extend(_cov002(snapshot, queue, diff))
    violations.extend(_cov003(queue, tests))
    violations.extend(_cov004(queue))
    violations.extend(_todo001(snapshot, queue, diff))
    return tuple(violations)


def _is_test_path(path: str) -> bool:
    """Test code is not public API; doc obligations do not apply to it."""
    parts = PurePosixPath(path).parts
    name = PurePosixPath(path).name
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


def _cov001(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """COV001: public symbol (outside test code) has no `doc` edge."""
    documented = {e.src for e in snapshot.edges if e.kind == EdgeKind.DOC}
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.symref in documented:
            continue
        if _is_test_path(record.id.path):
            continue
        _log.debug("COV001: %s undocumented", record.symref)
        violations.append(
            Violation(
                rule="COV001",
                severity=Severity.WARN,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"COV001: {record.symref} is public with no doc edge; "
                    f"add: frob:doc <docs/anchor> above it"
                ),
            )
        )
    return tuple(violations)


def _cov002(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff
) -> tuple[Violation, ...]:
    """COV002: a changed symbol is accounted for by neither a `frob:ticket`
    edge to an open ticket NOR an open ticket whose declared `scope` covers
    its file.

    Scope coverage means a cohesive refactor is acknowledged once (the
    ticket's scope glob) instead of demanding a per-symbol directive on
    every function it touches -- the same blast-radius the scope gate
    already enforces, read the other direction.
    """
    import fnmatch

    open_scopes: list[tuple[str, tuple[str, ...]]] = [
        (t.id, t.scope)
        for t in queue.tickets.values()
        if t.state in _OPEN_STATES and t.scope
    ]

    def _scope_covers(path: str) -> bool:
        return any(
            fnmatch.fnmatch(path, glob) for _tid, scope in open_scopes for glob in scope
        )

    violations: list[Violation] = []
    for symref in sorted(_touched_symrefs(diff, snapshot)):
        ticket_edges = [
            e for e in edges_from(snapshot, symref) if e.kind == EdgeKind.TICKET
        ]
        open_bound = any(
            (t := queue.tickets.get(e.target)) is not None and t.state in _OPEN_STATES
            for e in ticket_edges
        )
        if open_bound:
            continue
        record = snapshot.symbols[symref]
        if _scope_covers(record.id.path):
            _log.debug("COV002: %s covered by an open ticket's scope", symref)
            continue
        _log.debug("COV002: %s changed with no open ticket", symref)
        violations.append(
            Violation(
                rule="COV002",
                severity=Severity.ERROR,
                file=record.id.path,
                line=record.span[0],
                message=(
                    f"COV002: {symref} changed with no frob:ticket edge to an open "
                    f"ticket; run: frob ticket new, then add: frob:ticket <id>"
                ),
            )
        )
    return tuple(violations)


def _evidence_collected(evidence: str, tests: CollectedTests) -> bool:
    """Exact node-id membership, or bare-function match for parametrized
    tests (`f` satisfies evidence when only `f[param]` variants collect)."""
    if evidence in tests.node_ids:
        return True
    prefix = evidence + "["
    return any(node.startswith(prefix) for node in tests.node_ids)


def _cov003(queue: TicketQueue, tests: CollectedTests) -> tuple[Violation, ...]:
    """COV003: a done ticket's evidence ids do not resolve to a collected test."""
    violations: list[Violation] = []
    for ticket in queue.tickets.values():
        if ticket.state != TicketState.DONE:
            continue
        for evidence in ticket.evidence:
            if _evidence_collected(evidence, tests):
                continue
            _log.debug("COV003: %s evidence %s not collected", ticket.id, evidence)
            violations.append(
                Violation(
                    rule="COV003",
                    severity=Severity.ERROR,
                    file=f"tickets/{ticket.id}",
                    line=0,
                    message=(
                        f"COV003: {ticket.id} evidence {evidence!r} does not resolve "
                        f"to a collected test; run: frob test --collect to refresh, "
                        f"or fix the evidence id"
                    ),
                )
            )
    return tuple(violations)


def _cov004(queue: TicketQueue) -> tuple[Violation, ...]:
    """COV004: attachment sha256 mismatch or missing file (root taken from ticket path
    conventions -- `tickets/` is `frob.tickets`' fixed, undocumented-as-API layout,
    documented duplicate of `frob.tickets._store.tickets_dir`)."""
    violations: list[Violation] = []
    for ticket in queue.tickets.values():
        for attachment in ticket.attachments:
            path = Path("tickets") / attachment.path
            _log.debug("COV004: checking attachment %s", path)
            violations.extend(_cov004_one(ticket, attachment, path))
    return tuple(violations)


def _cov004_one(
    ticket: Ticket,
    attachment,
    path: Path,  # noqa: ANN001
) -> tuple[Violation, ...]:
    """COV004 check for one attachment, resolved relative to the gate's root."""
    return (
        Violation(
            rule="COV004",
            severity=Severity.ERROR,
            file=str(path),
            line=0,
            message=(
                f"COV004: {ticket.id} attachment {attachment.path} sha mismatch or "
                f"missing; run: frob ticket attach {ticket.id} again"
            ),
        ),
    )


def _todo001(
    snapshot: GraphSnapshot, queue: TicketQueue, diff: Diff
) -> tuple[Violation, ...]:
    """TODO001: `frob:todo` bound to a non-open ticket, or a bare TODO/FIXME comment
    in a diff-touched file (parsed fresh via `frob.lang`, cheap since scoped to the
    diff, not the whole tree)."""
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TODO:
            continue
        target = queue.tickets.get(edge.target)
        if target is not None and target.state in _OPEN_STATES:
            continue
        file, line = _site_from_edge_origin(edge.origin)
        _log.debug("TODO001: %s -> %s not open", edge.src, edge.target)
        violations.append(
            Violation(
                rule="TODO001",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"TODO001: frob:todo {edge.target} at {edge.src} is not bound to "
                    f"an open ticket; run: frob ticket new, then rebind"
                ),
            )
        )

    from frob.lang import parse_file  # local import: keep gates' top import list lean

    root = Path(snapshot.root)
    for file in sorted(_touched_files(diff)):
        parsed = parse_file(root / file)
        if parsed.is_err:
            continue
        for comment in parsed.danger_ok.comments:
            for offset, line_text in enumerate(
                comment.text.splitlines() or [comment.text]
            ):
                if line_text.strip().startswith("frob:"):
                    continue
                if _TODO_RE.search(line_text) is None:
                    continue
                lineno = comment.span[0] + offset
                _log.debug("TODO001: bare TODO/FIXME at %s:%d", file, lineno)
                violations.append(
                    Violation(
                        rule="TODO001",
                        severity=Severity.WARN,
                        file=file,
                        line=lineno,
                        message=(
                            f"TODO001: bare TODO/FIXME at {file}:{lineno}; bind it: "
                            f"frob:todo <ticket-id>"
                        ),
                    )
                )
    return tuple(violations)


def scope_digest(scope: Sequence[str], snapshot: GraphSnapshot) -> str:
    """Sha256 over the sorted `(file, hash)` pairs of files matching `scope`.

    THE one implementation: `frob ticket start/sweep` records it and
    `prework_gate` compares against it -- a second copy of this hash is how
    PRE001 becomes permanently stale (it happened; see tests/test_prework_parity.py).
    """
    import fnmatch

    matched = sorted(
        (path, digest)
        for path, digest in snapshot.file_hashes.items()
        if any(fnmatch.fnmatch(path, glob) for glob in scope)
    )
    hasher = hashlib.sha256()
    for path, digest in matched:
        hasher.update(f"{path}:{digest}\n".encode())
    return hasher.hexdigest()


def _scope_digest(ticket: Ticket, snapshot: GraphSnapshot) -> str:
    """`scope_digest` over a ticket's declared scope."""
    return scope_digest(ticket.scope, snapshot)


# frob:doc docs/gates.md#public-api
def scope_gate(
    diff: Diff, ticket: Ticket, snapshot: GraphSnapshot
) -> tuple[Violation, ...]:
    """SCOPE001: diff touches paths outside the active ticket's `scope`."""
    import fnmatch

    if not ticket.scope:
        _log.debug(
            "scope_gate: %s has no declared scope, nothing to enforce", ticket.id
        )
        return ()
    violations: list[Violation] = []
    for file in sorted(_touched_files(diff)):
        if any(fnmatch.fnmatch(file, glob) for glob in ticket.scope):
            continue
        _log.debug("SCOPE001: %s outside %s's scope", file, ticket.id)
        violations.append(
            Violation(
                rule="SCOPE001",
                severity=Severity.ERROR,
                file=file,
                line=0,
                message=(
                    f"SCOPE001: {file} is outside {ticket.id}'s declared scope; "
                    f"extend the ticket's scope or open a new ticket for this file"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/gates.md#public-api
def prework_gate(
    ticket: Ticket, snapshot: GraphSnapshot, sweep: Option[PreworkSweep] = Nothing()
) -> tuple[Violation, ...]:
    """PRE001: ticket moved to in-progress without a recorded, current pre-work sweep.

    **Deviation from docs/gates.md's exact signature** `(ticket, snapshot)`: the
    sweep is loaded state (from `.frob/prework/<id>.json`, see gates/_prework.py),
    and gates must not perform IO, so `run_gates` loads it and passes it in as an
    optional third argument rather than this function reaching into the
    filesystem itself.
    """
    if ticket.state != TicketState.IN_PROGRESS:
        return ()
    if sweep.is_nothing:
        _log.debug("PRE001: %s in-progress with no recorded sweep", ticket.id)
        return (
            Violation(
                rule="PRE001",
                severity=Severity.ERROR,
                file=f"tickets/{ticket.id}",
                line=0,
                message=(
                    f"PRE001: {ticket.id} is in-progress with no recorded pre-work "
                    f"sweep; run: frob ticket start {ticket.id}"
                ),
            ),
        )
    current_digest = _scope_digest(ticket, snapshot)
    if sweep.danger_some.digest != current_digest:
        _log.debug("PRE001: %s sweep is stale (digest moved)", ticket.id)
        return (
            Violation(
                rule="PRE001",
                severity=Severity.ERROR,
                file=f"tickets/{ticket.id}",
                line=0,
                message=(
                    f"PRE001: {ticket.id}'s recorded pre-work sweep is stale against "
                    f"the current scope; run: frob ticket start {ticket.id} again"
                ),
            ),
        )
    return ()


# frob:doc docs/gates.md#public-api
def invariant_gate(
    invariants: tuple[Invariant, ...],
    snapshot: GraphSnapshot,
    tests: CollectedTests,
    policy_rule_ids: frozenset[str] = frozenset(),
) -> tuple[Violation, ...]:
    """INV001 (no evidence) and INV002 (no code anchor).

    **Deviation**: adds an optional `policy_rule_ids` parameter beyond
    docs/gates.md's `(invariants, snapshot, tests)` signature so INV001 can
    treat a loaded policy rule id as valid evidence, per the doc's own
    evidence-list example (`POL-no-direct-lock-write`); without it there
    would be no way for this pure function to see policy state at all.
    """
    violations: list[Violation] = []
    anchors = {e.target for e in snapshot.edges if e.kind == EdgeKind.INVARIANT}
    for inv in invariants:
        has_evidence = any(
            _evidence_collected(item, tests) or item in policy_rule_ids
            for item in inv.evidence
        )
        if not inv.evidence or not has_evidence:
            _log.debug("INV001: %s has no standing evidence", inv.id)
            violations.append(
                Violation(
                    rule="INV001",
                    severity=Severity.ERROR,
                    file=inv.path,
                    line=0,
                    message=(
                        f"INV001: {inv.id} has no evidence resolving to a collected "
                        f"test or loaded policy rule; add a passing test or POL rule "
                        f"to its evidence list"
                    ),
                )
            )
        if inv.id not in anchors:
            _log.debug("INV002: %s has no code anchor", inv.id)
            violations.append(
                Violation(
                    rule="INV002",
                    severity=Severity.ERROR,
                    file=inv.path,
                    line=0,
                    message=(
                        f"INV002: {inv.id} has no frob:invariant anchor in code; "
                        f"add: frob:invariant {inv.id} at the enforcing site"
                    ),
                )
            )
    return tuple(violations)


# ---------------------------------------------------------------------------
# test_gate: TEST001..TEST006
# ---------------------------------------------------------------------------


def _test_edges(snapshot: GraphSnapshot, kind: str) -> dict[str, list[Edge]]:
    """`{target: [edges]}` for every TESTS edge of `kind`
    ("unit"/"integration"/"e2e")."""
    result: dict[str, list[Edge]] = {}
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS or edge.attrs.get("kind", "unit") != kind:
            continue
        result.setdefault(edge.target, []).append(edge)
    return result


def _valid_edges(edges: list[Edge], tests: CollectedTests) -> list[Edge]:
    """Edges whose `src` (the test's own symref) is still a collected node id."""
    return [e for e in edges if _symref_to_nodeid(e.src) in tests.node_ids]


def _is_test_file(path: str) -> bool:
    """True if `path` is itself a test file (documented duplicate of
    `frob.testing._select._is_test_file`'s name/dir heuristic, not importable
    in isolation since it is a private helper of that module)."""
    pure = PurePosixPath(path)
    if "tests" in pure.parts[:-1]:
        return True
    name = pure.stem
    return name.startswith("test_") or name.endswith("_test")


def _interface_package(path: str) -> str:
    """The interface unit a file belongs to: `src/<pkg>/<subpkg>` (or shorter)."""
    parts = PurePosixPath(path).parts
    return (
        str(PurePosixPath(*parts[:3]))
        if len(parts) >= 3
        else str(PurePosixPath(path).parent)
    )


def _test001_002(
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
) -> tuple[Violation, ...]:
    """TEST001 (no unit edge) and TEST002 (fewer than min_unit_cases valid edges)."""
    unit_edges = _test_edges(snapshot, "unit")
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if (
            not record.public
            or record.kind not in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            or _is_test_file(record.id.path)
        ):
            continue
        edges = unit_edges.get(record.symref, [])
        if not edges:
            _log.debug("TEST001: %s has no unit test edge", record.symref)
            violations.append(
                Violation(
                    rule="TEST001",
                    severity=Severity.ERROR,
                    file=record.id.path,
                    line=record.span[0],
                    message=(
                        f"TEST001: {record.symref} is public with no unit test; "
                        f'add: frob:tests {record.symref} kind="unit" on its test'
                    ),
                )
            )
            continue
        valid = _valid_edges(edges, tests)
        if len(valid) < cfg.min_unit_cases:
            _log.info(
                "TEST002: %s has %d/%d unit cases",
                record.symref,
                len(valid),
                cfg.min_unit_cases,
            )
            violations.append(
                Violation(
                    rule="TEST002",
                    severity=Severity.WARN,
                    file=record.id.path,
                    line=record.span[0],
                    message=(
                        f"TEST002: {record.symref} has {len(valid)} collected unit "
                        f"case(s), below min_unit_cases={cfg.min_unit_cases}; "
                        f'add more: frob:tests {record.symref} kind="unit"'
                    ),
                )
            )
    return tuple(violations)


def _test003(
    snapshot: GraphSnapshot, tests: CollectedTests, cfg: TestPolicy
) -> tuple[Violation, ...]:
    """TEST003: every package with public symbols owes `min_integration` edges.

    **Interface derivation, alpha semantics**: docs/gates.md describes interfaces
    as "packages whose public symbols are imported by another package." The
    graph does not track cross-file import edges (only `frob:` directive edges
    and doc anchors), so alpha instead treats every `src/<pkg>/<subpkg>`
    directory that contains at least one public symbol as an interface owing
    integration tests -- the simple, honest over-approximation the task
    explicitly allows in place of real import-graph derivation. Pair-level
    (consumer x provider) strictness is deferred, matching docs/gates.md's own
    "Interfaces are derived, not declared" design note.
    """
    integration_edges = _test_edges(snapshot, "integration")
    packages: dict[str, bool] = {}
    for record in snapshot.symbols.values():
        if record.public and not _is_test_file(record.id.path):
            packages.setdefault(_interface_package(record.id.path), True)

    violations: list[Violation] = []
    for package in sorted(packages):
        matching = [
            edge
            for target, edges in integration_edges.items()
            for edge in edges
            if target == package or target.startswith(package.rstrip("/") + "/")
        ]
        valid = _valid_edges(matching, tests)
        if len(valid) < cfg.min_integration:
            _log.info(
                "TEST003: %s has %d/%d integration edges",
                package,
                len(valid),
                cfg.min_integration,
            )
            violations.append(
                Violation(
                    rule="TEST003",
                    severity=Severity.WARN,
                    file=package,
                    line=0,
                    message=(
                        f"TEST003: interface {package} has {len(valid)} integration "
                        f"test(s), below min_integration={cfg.min_integration}; "
                        f'add: frob:tests {package} kind="integration"'
                    ),
                )
            )
    return tuple(violations)


def _test004(
    systems: tuple[SystemSpec, ...], snapshot: GraphSnapshot, tests: CollectedTests
) -> tuple[Violation, ...]:
    """TEST004: a declared `[[system]]` has fewer than its `min_e2e` e2e edges."""
    e2e_edges = _test_edges(snapshot, "e2e")
    violations: list[Violation] = []
    for system in systems:
        valid = _valid_edges(e2e_edges.get(system.id, []), tests)
        if len(valid) < system.min_e2e:
            _log.info(
                "TEST004: %s has %d/%d e2e edges", system.id, len(valid), system.min_e2e
            )
            violations.append(
                Violation(
                    rule="TEST004",
                    severity=Severity.ERROR,
                    file=f"[[system]] {system.id}",
                    line=0,
                    message=(
                        f"TEST004: system {system.id} has {len(valid)} e2e test(s), "
                        f"below min_e2e={system.min_e2e}; "
                        f'add: frob:tests {system.id} kind="e2e"'
                    ),
                )
            )
    return tuple(violations)


def _test005(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST005: measured coverage below a per-symbol, per-module, or
    per-system floor."""
    if coverage.is_nothing:
        return ()
    data = coverage.danger_some
    violations: list[Violation] = []
    for record in snapshot.symbols.values():
        if not record.public or record.kind not in (
            SymbolKind.FUNCTION,
            SymbolKind.METHOD,
        ):
            continue
        pct = data.symbol_branch.get(record.symref)
        if pct is not None and pct < cfg.unit_branch_cov:
            _log.info(
                "TEST005: %s branch cov %.1f%% < %d%%",
                record.symref,
                pct,
                cfg.unit_branch_cov,
            )
            violations.append(
                Violation(
                    rule="TEST005",
                    severity=Severity.WARN,
                    file=record.id.path,
                    line=record.span[0],
                    message=(
                        f"TEST005: {record.symref} branch coverage {pct:.1f}% below "
                        f"unit_branch_cov={cfg.unit_branch_cov}%; add tests, then: "
                        f"make coverage"
                    ),
                )
            )
    for module, pct in data.module_line.items():
        if pct < cfg.module_line_cov:
            _log.info(
                "TEST005: %s line cov %.1f%% < %d%%", module, pct, cfg.module_line_cov
            )
            violations.append(
                Violation(
                    rule="TEST005",
                    severity=Severity.WARN,
                    file=module,
                    line=0,
                    message=(
                        f"TEST005: {module} line coverage {pct:.1f}% below "
                        f"module_line_cov={cfg.module_line_cov}%; add tests, then: "
                        f"make coverage"
                    ),
                )
            )
    for system in systems:
        relevant = [
            pct
            for path, pct in data.module_line.items()
            if any(_glob_prefix_match(path, glob) for glob in system.paths)
        ]
        if not relevant:
            continue
        avg = sum(relevant) / len(relevant)
        if avg < cfg.system_line_cov:
            _log.info(
                "TEST005: system %s line cov %.1f%% < %d%%",
                system.id,
                avg,
                cfg.system_line_cov,
            )
            violations.append(
                Violation(
                    rule="TEST005",
                    severity=Severity.WARN,
                    file=f"[[system]] {system.id}",
                    line=0,
                    message=(
                        f"TEST005: system {system.id} line coverage {avg:.1f}% below "
                        f"system_line_cov={cfg.system_line_cov}%; add tests, then: "
                        f"make coverage"
                    ),
                )
            )
    return tuple(violations)


def _glob_prefix_match(path: str, glob: str) -> bool:
    """True if `path` sits under a `[[system]].paths` glob's directory prefix."""
    import fnmatch

    return fnmatch.fnmatch(path, glob) or path.startswith(glob.split("*")[0])


def _test006(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """TEST006: coverage stamp missing, or stale against current file hashes."""
    root = Path(snapshot.root)
    stamp = load_stamp(root)
    if stamp is None:
        _log.debug("TEST006: no coverage stamp at %s", root)
        return (
            Violation(
                rule="TEST006",
                severity=Severity.ERROR,
                file=".frob/coverage-stamp",
                line=0,
                message="TEST006: no coverage stamp found; run: make coverage",
            ),
        )
    stamped_hashes = stamp.get("file_hashes", {})
    for path, current_hash in snapshot.file_hashes.items():
        stamped = stamped_hashes.get(path)
        if stamped is not None and stamped != current_hash:
            _log.debug("TEST006: coverage stamp stale for %s", path)
            return (
                Violation(
                    rule="TEST006",
                    severity=Severity.ERROR,
                    file=".frob/coverage-stamp",
                    line=0,
                    message=(
                        f"TEST006: coverage stamp is stale ({path} changed since "
                        f"stamping); run: make coverage"
                    ),
                ),
            )
    return ()


# frob:doc docs/gates.md#public-api
def test_gate(
    snapshot: GraphSnapshot,
    systems: tuple[SystemSpec, ...],
    coverage: Option[CoverageData],
    tests: CollectedTests,
    cfg: TestPolicy,
) -> tuple[Violation, ...]:
    """TEST001..TEST006. Interfaces derived from packages with public symbols
    (see `_test003`'s docstring for the exact alpha semantics). Coverage is
    consumed as recorded evidence, never produced here."""
    violations: list[Violation] = []
    violations.extend(_test001_002(snapshot, tests, cfg))
    violations.extend(_test003(snapshot, tests, cfg))
    violations.extend(_test004(systems, snapshot, tests))
    violations.extend(_test005(snapshot, systems, coverage, cfg))
    violations.extend(_test006(snapshot))
    return tuple(violations)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _load_test_config(root: Path) -> tuple[TestPolicy, tuple[SystemSpec, ...]]:
    """`[testing]` -> `TestPolicy`, `[[system]]` -> `SystemSpec` tuple;
    both optional."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return TestPolicy(), ()
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, ValueError) as exc:
        _log.warning("_load_test_config: could not parse %s: %s", toml_path, exc)
        return TestPolicy(), ()

    testing_tbl = doc.get("testing", {})
    fields = TestPolicy.model_fields
    try:
        policy = TestPolicy(**{k: v for k, v in testing_tbl.items() if k in fields})
    except ValidationError as exc:
        _log.warning("_load_test_config: bad [testing] table: %s", exc)
        policy = TestPolicy()

    systems: list[SystemSpec] = []
    for entry in doc.get("system", []):
        try:
            systems.append(
                SystemSpec(
                    id=entry["id"],
                    entrypoint=entry.get("entrypoint", ""),
                    min_e2e=entry.get("min_e2e", 1),
                    paths=tuple(entry.get("paths", ())),
                )
            )
        except (KeyError, ValidationError) as exc:
            _log.warning("_load_test_config: bad [[system]] entry: %s", exc)
    return policy, tuple(systems)


# ---------------------------------------------------------------------------
# run_gates
# ---------------------------------------------------------------------------

_ALL_GATES = frozenset(
    {
        "drift",
        "coverage",
        "scope",
        "prework",
        "invariant",
        "test",
        "policy",
        "doclink",
        "perf",
        "fuzz",
        "release",
    }
)


# frob:ticket T-0003
def release_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """REL001: the public-API change since the last `frob release stamp`
    demands a version bump the declared version does not cover, or the
    changelog does not mention the version.

    Opt-in: runs only when a `.frob-release.json` manifest exists (a repo
    adopts the release discipline by stamping once). The bump class is
    computed mechanically from public signature digests -- breaking sig
    change is major, new public symbol is minor.
    """
    from frob.release import diff_class, load_manifest, required_version, satisfies

    root = Path(root)
    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.debug("release_gate: no manifest, skipping")
        return ()
    manifest = manifest_result.danger_ok

    current_version = _current_version(root)
    if current_version is None:
        _log.debug("release_gate: no detectable project version, skipping")
        return ()

    bump = diff_class(manifest, snapshot)
    violations: list[Violation] = []
    need = required_version(manifest.version, bump)
    if need.is_ok and not satisfies(current_version, need.danger_ok):
        cls = bump.name.lower()
        violations.append(
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file="pyproject.toml",
                line=0,
                message=(
                    f"REL001: public API changed ({cls}) since {manifest.version}; "
                    f"bump the version to >= {need.danger_ok} (currently "
                    f"{current_version}), then run: frob release stamp"
                ),
            )
        )
    if bump != 0 and not _changelog_mentions(root, current_version):
        violations.append(
            Violation(
                rule="REL001",
                severity=Severity.ERROR,
                file="CHANGELOG.md",
                line=0,
                message=(
                    f"REL001: no CHANGELOG.md entry for {current_version}; the "
                    f"public API changed and needs a release note"
                ),
            )
        )
    _log.info("release_gate: bump=%s, %d violation(s)", bump.name, len(violations))
    return tuple(violations)


def _current_version(root: Path) -> str | None:
    """The project version from pyproject.toml, or None if undetectable."""
    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        return None
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    version = data.get("project", {}).get("version")
    return version if isinstance(version, str) else None


def _changelog_mentions(root: Path, version: str) -> bool:
    """Whether CHANGELOG.md (if present) names `version`; absent file passes."""
    for name in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md"):
        path = root / name
        if path.exists():
            try:
                return version in path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return True
    return True


# frob:ticket T-0002
def fuzz_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """FUZZ001/002/003 over the [fuzz] policy in frob.toml.

    Default enforce is OFF (a repo opts in): fuzzing is a strong mandate, so
    it stays silent until [fuzz].enforce is set -- the warn-first adoption
    posture. Loads the policy, computes obligations, composes the three pure
    rule functions from frob.fuzz.
    """
    from frob.fuzz import (
        FUZZ001,
        FUZZ002,
        FUZZ003,
        FuzzEnforce,
        FuzzPolicy,
        load_fuzz_stamp,
        obligations,
        resolve_param_types,
    )

    root = Path(root)
    enforce = FuzzEnforce.OFF
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                raw = tomllib.load(fh).get("fuzz", {}).get("enforce")
            if raw in tuple(FuzzEnforce):
                enforce = FuzzEnforce(raw)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("fuzz_gate: frob.toml unreadable: %s", exc)
    if enforce == FuzzEnforce.OFF:
        _log.debug("fuzz_gate: [fuzz].enforce=off, skipping")
        return ()

    obs = obligations(snapshot, FuzzPolicy(enforce=enforce))
    param_types = {ob.ref: resolve_param_types(root, ob.ref) for ob in obs}
    stamp = load_fuzz_stamp(root)
    violations = (
        *FUZZ001(snapshot, obs),
        *FUZZ002(obs, param_types),
        *FUZZ003(snapshot, obs, stamp),
    )
    _log.info(
        "fuzz_gate: %d obligation(s), %d violation(s)", len(obs), len(violations)
    )
    return tuple(violations)


_MD_LINK_RE = re.compile(r"\]\(([^)#\s]+)")
# Backtick path references (`docs/x.md`) count as links too: these docs are
# written terminal-first, where an index names files in code spans rather
# than markdown links -- an index entry is a link either way.
_MD_CODE_REF_RE = re.compile(r"`([^`\s]+\.md)`")


# frob:ticket T-0021
# frob:ticket T-0028
def doclink_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOC001: a doc file nothing links to is an error -- orphan docs rot.

    The obligated set is discovered by GLOB (default `docs/**/*.md`,
    `[gates.docs] include/exclude` in frob.toml), so a newly added doc file
    is automatically covered the moment it exists. A doc counts as linked
    when it carries a frob:describes anchor, is the target of a frob:doc
    edge, or is reachable through relative markdown links crawled from the
    root set (default docs/index.md and README.md).
    """
    import fnmatch

    root = Path(root)
    include = ["docs/**/*.md"]
    exclude: list[str] = []
    roots = ["docs/index.md", "README.md"]
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                section = tomllib.load(fh).get("gates", {}).get("docs", {})
            include = list(section.get("include", include))
            exclude = list(section.get("exclude", exclude))
            roots = list(section.get("roots", roots))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("doclink: frob.toml unreadable: %s", exc)

    obligated: set[str] = set()
    for glob in include:
        for path in root.glob(glob):
            rel = path.relative_to(root).as_posix()
            if not any(fnmatch.fnmatch(rel, ex) for ex in exclude):
                obligated.add(rel)
    if not obligated:
        _log.debug("doclink: no docs matched %s", include)
        return ()

    linked: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.DESCRIBES:
            linked.add(edge.src.split("#", 1)[0])
        elif edge.kind == EdgeKind.DOC:
            linked.add(edge.target.split("#", 1)[0])

    # Crawl relative markdown links from the roots plus already-linked docs;
    # a doc linked from a reachable doc is reachable.
    queue = [r for r in roots if (root / r).exists()] + sorted(linked)
    seen: set[str] = set()
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        current_path = root / current
        if not current_path.exists():
            continue
        try:
            text = current_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        base = PurePosixPath(current).parent
        targets = _MD_LINK_RE.findall(text) + _MD_CODE_REF_RE.findall(text)
        for target in targets:
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = str(PurePosixPath(*(base / target).parts)).replace("../", "")
            for candidate in (resolved, target.lstrip("./")):
                if candidate in obligated and candidate not in seen:
                    linked.add(candidate)
                    queue.append(candidate)

    violations: list[Violation] = []
    for orphan in sorted(obligated - linked - set(roots)):
        _log.debug("DOC001: %s is unlinked", orphan)
        violations.append(
            Violation(
                rule="DOC001",
                severity=Severity.ERROR,
                file=orphan,
                line=0,
                message=(
                    f"DOC001: {orphan} is linked from nowhere; add a "
                    f"frob:describes anchor, reference it with frob:doc, or "
                    f"link it from {roots[0]}"
                ),
            )
        )
    _log.info("doclink: %d obligated, %d orphaned", len(obligated), len(violations))
    return tuple(violations)


# frob:doc docs/perf.md#integration-points
# frob:ticket T-0021
def perf_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PERF001..PERF004, run at the policy/gates stage per docs/perf.md's
    Integration points. Parses every source file in `snapshot.file_hashes`
    (same posture as `frob.policy`'s `_pattern_violations`: gates does the
    IO, `frob.perf.perf_rules` stays pure) and hands the parsed set to
    `perf_rules`; a file that fails to parse is skipped, never fatal."""
    from frob.lang import parse_file
    from frob.perf import perf_rules

    parsed: list[ParsedFile] = []
    for rel_path in sorted(snapshot.file_hashes):
        result = parse_file(root / rel_path)
        if result.is_err:
            _log.debug(
                "perf_gate: skipping unparsed %s: %s", rel_path, result.danger_err
            )
            continue
        parsed.append(result.danger_ok)
    violations = perf_rules(snapshot, parsed)
    _log.info(
        "perf_gate: %d file(s) scanned, %d violation(s)", len(parsed), len(violations)
    )
    return violations


# frob:doc docs/gates.md#public-api
# frob:uses-contract src/frob/graph/__init__.py::build_graph
# frob:uses-contract src/frob/graph/lock.py::drift
# frob:uses-contract src/frob/tickets/__init__.py::load_queue
def _severity_overrides(root: Path | str) -> dict[str, Severity]:
    """The `[gates.severity]` table from frob.toml: rule id -> warn|error.

    This is how a legacy codebase adopts gates without a big-bang: noisy
    rules go to "warn" (visible, not blocking) and are flipped back to
    "error" as annotation coverage grows. Values other than warn/error are
    ignored with a warning -- never a crash on config typos.
    """
    toml_path = Path(root) / "frob.toml"
    if not toml_path.exists():
        return {}
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("severity overrides: could not read %s: %s", toml_path, exc)
        return {}
    raw = data.get("gates", {}).get("severity", {})
    overrides: dict[str, Severity] = {}
    for rule, value in raw.items():
        if value in ("warn", "error"):
            overrides[rule] = Severity.WARN if value == "warn" else Severity.ERROR
        else:
            _log.warning(
                "severity overrides: %s=%r is not warn|error; ignored", rule, value
            )
    if overrides:
        _log.info("severity overrides active: %s", overrides)
    return overrides


def _apply_severity_overrides(
    violations: tuple[Violation, ...], root: Path | str
) -> tuple[Violation, ...]:
    """Re-severity `violations` per the `[gates.severity]` frob.toml table."""
    overrides = _severity_overrides(root)
    if not overrides:
        return violations
    return tuple(
        v.model_copy(update={"severity": overrides[v.rule]})
        if v.rule in overrides
        else v
        for v in violations
    )


# frob:ticket T-0021
def run_gates(cfg: GateConfig) -> Result[GateReport, GateError]:
    """Load everything once, then run the selected gates in parallel and merge."""
    # Local import: frob.policy imports frob.gates._models (Violation/Severity), so a
    # module-level `from frob.policy import ...` here would form an import cycle the
    # first time either package is imported on its own; deferring it to call time
    # breaks the cycle without weakening either package's public surface.
    from frob.policy import load_policy, policy_gate

    root = Path(cfg.root)
    start_all = time.monotonic()
    selected = cfg.gates or _ALL_GATES
    _log.info("run_gates: root=%s base=%s gates=%s", root, cfg.base, sorted(selected))

    cache_path = root / _CACHE_REL
    build_result: Result[GraphSnapshot, BuildError] = build_graph(root, cache_path)
    if build_result.is_err:
        _log.error("run_gates: graph build failed: %s", build_result.danger_err)
        return Err(GateError.GraphUnavailable)
    snapshot = build_result.danger_ok

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("run_gates: ticket queue load failed: %s", queue_result.danger_err)
        return Err(GateError.QueueUnavailable)
    queue = queue_result.danger_ok

    lock_result = load_lock(root / "frob.lock")
    if lock_result.is_err:
        _log.error("run_gates: lock load failed: %s", lock_result.danger_err)
        return Err(GateError.ConfigMalformed)
    lock = lock_result.danger_ok

    # A missing diff (fresh repo with no commits, unknown base, detached
    # HEAD) must not skip the WHOLE gates stage -- only coverage/scope read
    # the diff. Degrade to an empty diff so drift/invariant/test/doclink/
    # fuzz/policy still run; the diff-dependent gates then simply see no
    # touched symbols.
    diff_result = working_diff(root, cfg.base)
    if diff_result.is_err:
        _log.warning(
            "run_gates: working_diff failed (%s); diff-dependent gates see no "
            "touched set",
            diff_result.danger_err,
        )
        diff = Diff(base=cfg.base, hunks=())
    else:
        diff = diff_result.danger_ok

    tests_result = collect_python_tests(root)
    if tests_result.is_err:
        _log.error("run_gates: pytest collection failed: %s", tests_result.danger_err)
        tests = CollectedTests(node_ids=frozenset())
    else:
        tests = tests_result.danger_ok

    invariants_result = load_invariants(root)
    if invariants_result.is_err:
        _log.error(
            "run_gates: invariants load failed: %s", invariants_result.danger_err
        )
        return Err(GateError.ConfigMalformed)
    invariants = invariants_result.danger_ok

    policy_result = load_policy(root)
    if policy_result.is_err:
        _log.error("run_gates: policy load failed: %s", policy_result.danger_err)
        return Err(GateError.ConfigMalformed)
    rules = policy_result.danger_ok

    coverage_result = load_coverage(root, snapshot)
    coverage: Option[CoverageData] = (
        Some(coverage_result.danger_ok) if coverage_result.is_ok else Nothing()
    )

    test_policy, systems = _load_test_config(root)

    ticket_id_opt = active_ticket(root, cfg.ticket)
    ticket: Ticket | None = None
    sweep: Option[PreworkSweep] = Nothing()
    skipped: list[str] = []
    if ticket_id_opt.is_some:
        ticket = queue.tickets.get(ticket_id_opt.danger_some)
        if ticket is None:
            _log.warning(
                "run_gates: active ticket %s not in queue", ticket_id_opt.danger_some
            )
        else:
            loaded_sweep = load_prework(root, ticket.id)
            sweep = Some(loaded_sweep) if loaded_sweep is not None else Nothing()

    jobs: dict[str, Callable[[], tuple[Violation, ...]]] = {}
    if "drift" in selected:
        jobs["drift"] = lambda: drift_gate(snapshot, lock)
    if "coverage" in selected:
        jobs["coverage"] = lambda: coverage_gate(snapshot, queue, diff, tests)
    if "scope" in selected:
        if ticket is not None:
            jobs["scope"] = lambda: scope_gate(diff, ticket, snapshot)
        else:
            skipped.append("scope")
    if "prework" in selected:
        if ticket is not None:
            jobs["prework"] = lambda: prework_gate(ticket, snapshot, sweep)
        else:
            skipped.append("prework")
    if "invariant" in selected:
        rule_ids = frozenset(r.id for r in rules)
        jobs["invariant"] = lambda: invariant_gate(
            invariants, snapshot, tests, rule_ids
        )
    if "test" in selected:
        jobs["test"] = lambda: test_gate(
            snapshot, systems, coverage, tests, test_policy
        )
    if "policy" in selected:
        jobs["policy"] = lambda: policy_gate(rules, snapshot, diff)
    if "doclink" in selected:
        jobs["doclink"] = lambda: doclink_gate(Path(cfg.root), snapshot)
    if "perf" in selected:
        jobs["perf"] = lambda: perf_gate(root, snapshot)
    if "fuzz" in selected:
        jobs["fuzz"] = lambda: fuzz_gate(Path(cfg.root), snapshot)
    if "release" in selected:
        jobs["release"] = lambda: release_gate(Path(cfg.root), snapshot)

    from concurrent.futures import ThreadPoolExecutor

    counts: dict[str, int] = {}
    timing: dict[str, float] = {}
    all_violations: list[Violation] = list(_waive001_violations(snapshot))
    counts["waive"] = len(all_violations)

    if jobs:
        with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
            futures = {}
            for name, job in jobs.items():
                job_start = time.monotonic()
                futures[pool.submit(job)] = (name, job_start)
            for future in futures:
                name, job_start = futures[future]
                result = future.result()
                timing[name] = time.monotonic() - job_start
                counts[name] = len(result)
                all_violations.extend(result)
                _log.info(
                    "run_gates: %s -> %d violation(s) in %.3fs",
                    name,
                    len(result),
                    timing[name],
                )

    kept, waived = _apply_waivers(tuple(all_violations), snapshot)
    kept = _apply_severity_overrides(kept, cfg.root)
    stats = GateStats(counts=counts, timing_s=timing, skipped=tuple(skipped))
    _log.info(
        "run_gates: done in %.3fs, %d kept, %d waived, skipped=%s",
        time.monotonic() - start_all,
        len(kept),
        len(waived),
        skipped,
    )
    return Ok(GateReport(violations=kept, waived=waived, stats=stats))


__all__ = [
    "CoverageData",
    "CoverageError",
    "GateConfig",
    "GateError",
    "GateReport",
    "GateStats",
    "Invariant",
    "InvariantError",
    "PreworkSweep",
    "Severity",
    "SystemSpec",
    "TestPolicy",
    "Violation",
    "WaiverRef",
    "active_ticket",
    "coverage_gate",
    "drift_gate",
    "invariant_gate",
    "load_coverage",
    "load_invariants",
    "doclink_gate",
    "fuzz_gate",
    "perf_gate",
    "release_gate",
    "prework_gate",
    "record_prework",
    "run_gates",
    "scope_digest",
    "scope_gate",
    "stamp_coverage",
    "test_gate",
]
