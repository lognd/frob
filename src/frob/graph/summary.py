"""Per-function protocol-summary fixpoint engine.

docs/modules/graph.md#protocol-summary-engine.

Child 2 of T-0739: a shared, bottom-up fixpoint over `frob.graph.callgraph
.CallGraph` that summarizes every reachable function's contribution to the
T-0744 typestate-protocol DSL (`frob:protocol`/`frob:transition`/
`frob:requires`, `EdgeKind.PROTOCOL`/`TRANSITION`/`REQUIRES`): which
protocol states it REQUIRES on entry and which state TRANSITIONS it may
perform, transitively through everything it calls. Built once here so a
future consumer (T-0686 may-raise -- DESIGN CONSTRAINT in T-0745: one
engine, not two) can host its own lattice over the exact same SCC-ordered
worklist instead of re-deriving call-graph traversal.

NO-FAIL-SILENT (user mandate, T-0745 acceptance): an unresolved callee
(`UNRESOLVED_CALLEE`) POISONS the calling function's summary and every
transitive caller of it -- poisoning propagates, it never resets. A
function outside the reachable set (unreachable from every entrypoint
passed in) is reported in `SummaryResult.not_analyzed`, never silently
given an empty summary. A recursive SCC that fails to reach a fixpoint
within `max_iterations` is reported in `SummaryResult.timeouts` naming the
SCC, and every member of that SCC is poisoned -- an engine abort is an
ERROR surfaced to the caller, never a quiet partial result.

Deliberately deterministic and offline: callers build (or fabricate, in
tests) a `CallGraph` + `Edge` sequence up front: this module performs no
filesystem walk of its own.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.graph._models import Edge, EdgeKind
from frob.graph.callgraph import UNRESOLVED_CALLEE, CallGraph
from frob.logging import get_logger

__all__ = [
    "UNRESOLVED_CALLEE",
    "ConfinementCensusResult",
    "ConfinementState",
    "FsWriteSite",
    "FunctionConfinement",
    "FunctionSummary",
    "SCCTimeout",
    "SummaryResult",
    "compute_confinement_summaries",
    "compute_protocol_summaries",
    "scan_confinement_facts",
]

_log = get_logger(__name__)

# frob:ticket T-0809
# Re-exported from `frob.graph.callgraph` (T-0809) -- ONE sentinel string,
# not two. `callgraph.build_call_graph` is now the real producer of this
# edge (see its `mark_unresolved` parameter); this module remains the
# consumer that defines what the sentinel DOES to a summary
# (NO-FAIL-SILENT poisoning, module docstring). Kept as a name in THIS
# module's own namespace (not just relying on the import) for backward
# compatibility with every existing `frob.graph.summary.UNRESOLVED_CALLEE`
# reference (tests, docs) predating this ticket. The `import ... as` above
# already binds the name in this module's namespace; nothing further to
# do here beyond the `__all__` re-export.

_DEFAULT_MAX_ITERATIONS = 100

# frob:ticket T-0809
# `(requires, transitions, acquired, released, escaped)` -- the five
# string-sets carried through `_own_contribution`/`_join_from_callees`'s
# join step. A type alias, not a model, to match `requires`/`transitions`'
# existing plain-`frozenset[str]` posture (a lattice join is just set
# union); named only to keep the two functions' signatures under line
# length, not a new public shape.
_FiveSets = tuple[
    frozenset[str], frozenset[str], frozenset[str], frozenset[str], frozenset[str]
]
# `_FiveSets` plus the poisoning outcome `_join_from_callees` also returns.
_JoinResult = tuple[
    frozenset[str],
    frozenset[str],
    frozenset[str],
    frozenset[str],
    frozenset[str],
    bool,
    str | None,
]


def _own_contribution(symref: str, edges: Sequence[Edge]) -> _FiveSets:
    """`(requires, transitions, acquired, released, escaped)` string-sets this
    `symref` declares directly.

    `requires` entries render as `"proto:state"`, `transitions` entries as
    `"proto:from->to"` -- both are plain strings (not nested models) so a
    lattice join is just set union, and a hand-computed expected value in
    a test is a one-line set literal. T-0809: `acquired`/`released`/
    `escaped` are plain resource-name strings (`frob:acquire`/
    `frob:release`/`frob:escapes`), joined the same way."""
    requires: set[str] = set()
    transitions: set[str] = set()
    acquired: set[str] = set()
    released: set[str] = set()
    escaped: set[str] = set()
    for e in edges:
        if e.src != symref:
            continue
        if e.kind is EdgeKind.REQUIRES:
            proto = e.attrs.get("proto", e.target)
            state = e.attrs.get("state", "")
            requires.add(f"{proto}:{state}")
        elif e.kind is EdgeKind.TRANSITION:
            proto = e.attrs.get("proto", e.target)
            frm = e.attrs.get("from", "")
            to = e.attrs.get("to", "")
            transitions.add(f"{proto}:{frm}->{to}")
        elif e.kind is EdgeKind.ACQUIRE:
            acquired.add(e.target)
        elif e.kind is EdgeKind.RELEASE:
            released.add(e.target)
        elif e.kind is EdgeKind.ESCAPES:
            escaped.add(e.target)
    return (
        frozenset(requires),
        frozenset(transitions),
        frozenset(acquired),
        frozenset(released),
        frozenset(escaped),
    )


# frob:doc docs/modules/graph.md#protocol-summary-engine
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_leaf_resource_declarations_populate_acquired_released_escaped  # noqa: E501
class FunctionSummary(BaseModel):
    """One function's fixpoint-computed protocol contribution.

    `requires`/`transitions` are the transitive union over everything this
    function (directly or indirectly) calls, plus its own declarations.
    `poisoned` is `True` the moment any callee in the transitive closure is
    `UNRESOLVED_CALLEE` or itself poisoned -- `requires`/`transitions` are
    still populated with whatever WAS resolved (best-effort), but a
    consumer must treat a poisoned summary as untrustworthy, per the
    NO-FAIL-SILENT mandate (an ERROR downstream, never silence).

    T-0809: `acquired`/`released`/`escaped` are the same transitive-union
    treatment applied to the resource-tracking DSL (`frob:acquire`/
    `frob:release`/`frob:escapes`) -- plain resource-name string sets, not
    a net-held/leaked computation. Real postdominance-based cleanup
    verification (does every acquire on every exit path actually reach a
    release) is T-0747's job, blocked on this engine plus T-0686; this
    summary only exposes the raw transitive sets a later verifier needs,
    same posture as `requires`/`transitions` exposing declarations without
    themselves verifying anything against a call site."""

    model_config = ConfigDict(frozen=True)

    symref: str
    requires: frozenset[str] = frozenset()
    transitions: frozenset[str] = frozenset()
    acquired: frozenset[str] = frozenset()
    released: frozenset[str] = frozenset()
    escaped: frozenset[str] = frozenset()
    poisoned: bool = False
    poison_reason: str | None = None


# frob:doc docs/modules/graph.md#protocol-summary-engine
class SCCTimeout(BaseModel):
    """A strongly-connected (recursive) call cluster that did not converge
    within `max_iterations` -- an ERROR the caller must surface, never a
    silently-dropped partial summary (T-0745 acceptance)."""

    model_config = ConfigDict(frozen=True)

    members: tuple[str, ...]
    iterations: int


# frob:doc docs/modules/graph.md#protocol-summary-engine
class SummaryResult(BaseModel):
    """The full fixpoint run's output: summaries for every reachable
    function, plus the two loud-failure channels (`not_analyzed`,
    `timeouts`) the NO-FAIL-SILENT mandate requires never collapse into a
    quiet empty summary."""

    model_config = ConfigDict(frozen=True)

    summaries: Mapping[str, FunctionSummary] = {}
    not_analyzed: tuple[str, ...] = ()
    timeouts: tuple[SCCTimeout, ...] = ()


def _universe(
    callgraph: CallGraph, edges: Sequence[Edge], entrypoints: Sequence[str]
) -> set[str]:
    """Every symref this run could possibly need a summary for: entrypoints,
    every caller/callee in `callgraph`, and every declaring `src` in
    `edges` (a leaf function with a bare `frob:requires`/`frob:transition`
    and no calls of its own still needs a node to hang its summary on)."""
    nodes: set[str] = set(entrypoints)
    for caller, callees in callgraph.calls.items():
        nodes.add(caller)
        for callee in callees:
            if callee != UNRESOLVED_CALLEE:
                nodes.add(callee)
    for e in edges:
        if e.kind in (
            EdgeKind.REQUIRES,
            EdgeKind.TRANSITION,
            EdgeKind.ACQUIRE,
            EdgeKind.RELEASE,
            EdgeKind.ESCAPES,
        ):
            nodes.add(e.src)
    return nodes


# frob:ticket T-0972
def _reachable(
    callgraph: CallGraph, entrypoints: Sequence[str], universe: set[str]
) -> set[str]:
    """BFS forward closure (caller -> callee) from `entrypoints`, restricted
    to `universe` -- a function no entrypoint ever calls, transitively, is
    NOT reachable and must not receive a summary (`not_analyzed` instead)."""
    seen: set[str] = set()
    stack = [n for n in entrypoints if n in universe]
    seen.update(stack)
    # frob:waive PERF003 reason="DFS forward-closure over the call graph, one pass over edges O(V+E), not a cross join"  # noqa: E501
    while stack:
        node = stack.pop()
        for callee in callgraph.calls.get(node, ()):
            if callee == UNRESOLVED_CALLEE or callee in seen:
                continue
            seen.add(callee)
            stack.append(callee)
    return seen


# frob:waive ARCH001 reason="a textbook Tarjan's SCC (iterative, to avoid recursion-depth limits on large call graphs): index/lowlink/on-stack bookkeeping plus the explicit work-stack unwind loop are one indivisible algorithm, not independently meaningful phases -- splitting the unwind step into a helper would require passing the index/lowlink/stack triple across a new boundary for every visited node, adding indirection without separating a real sub-concern"  # noqa: E501
# arch-exempt: deep-nesting reason="T-1066: same textbook iterative Tarjan's SCC already reasoned about in this function's ARCH001 waiver above -- the depth-5 nesting here is the index/lowlink/on-stack bookkeeping interleaved with the explicit work-stack unwind and SCC-pop loop, one indivisible algorithm; a forced split would thread the index/lowlink/stack triple across a new boundary per visited node, adding indirection without separating a real sub-concern, which the standing ARCH001 rationale on this same function already established"  # noqa: E501
# frob:ticket T-0972
def _tarjan_sccs(nodes: Sequence[str], callgraph: CallGraph) -> list[list[str]]:
    """Tarjan's SCC decomposition over `nodes`, restricted to edges landing
    back inside `nodes` -- returns EVERY component (including singleton,
    non-cyclic nodes, unlike `frob.cycle.graph.find_cycles` which only
    reports size>1/self-looping components) in the order components are
    completed, which is exactly bottom-up (a callee's component always
    finishes, and is emitted, before its caller's) -- the order the
    fixpoint needs. A private, minimal implementation rather than reusing
    `frob.cycle.graph` (a different subsystem, out of this ticket's scope)
    to keep this module's only dependency the `CallGraph` shape it already
    consumes. Iterative (explicit work-stack), not recursive, so a deep
    real-world call chain never risks Python's recursion limit."""
    node_set = set(nodes)
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = 0

    def neighbors(v: str) -> list[str]:
        return [c for c in callgraph.calls.get(v, ()) if c in node_set]

    for start in sorted(node_set):
        if start in index:
            continue
        work: list[tuple[str, int]] = [(start, 0)]
        # frob:waive PERF003 reason="inherent to Tarjan SCC (iterative work-stack), one pass over edges, not a cross join"  # noqa: E501
        while work:
            v, pos = work[-1]
            if pos == 0:
                index[v] = counter
                lowlink[v] = counter
                counter += 1
                stack.append(v)
                on_stack.add(v)
            neigh = neighbors(v)
            i = pos
            descended = False
            while i < len(neigh):
                w = neigh[i]
                if w not in index:
                    work[-1] = (v, i + 1)
                    work.append((w, 0))
                    descended = True
                    break
                if w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])
                i += 1
            if descended:
                continue
            work[-1] = (v, len(neigh))
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[v])
            if lowlink[v] == index[v]:
                scc: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == v:
                        break
                # frob:waive PERF004 reason="inherent to Tarjan SCC: scc is this component's own distinct node list, not a shared re-sort"  # noqa: E501
                sccs.append(sorted(scc))
    return sccs


def _join_from_callees(
    member: str,
    own_req: frozenset[str],
    own_trans: frozenset[str],
    own_acquired: frozenset[str],
    own_released: frozenset[str],
    own_escaped: frozenset[str],
    own_poisoned: bool,
    callgraph: CallGraph,
    lookup: Mapping[str, FunctionSummary],
) -> _JoinResult:
    """One join step for `member`: its own declarations unioned with every
    callee's CURRENT summary in `lookup` (cross-SCC callees are final by
    the time this runs; intra-SCC callees are this round's in-progress
    values) -- the lattice-join core both the single-node and recursive-
    SCC branches of `compute_protocol_summaries` share. T-0809: the
    resource sets (`acquired`/`released`/`escaped`) join by the same plain
    set-union rule as `requires`/`transitions`."""
    requires = set(own_req)
    transitions = set(own_trans)
    acquired = set(own_acquired)
    released = set(own_released)
    escaped = set(own_escaped)
    poisoned = own_poisoned
    reason: str | None = None
    for callee in callgraph.calls.get(member, ()):
        if callee == UNRESOLVED_CALLEE:
            poisoned = True
            reason = reason or f"{member} calls an unresolved callee"
            continue
        callee_summary = lookup.get(callee)
        if callee_summary is None:
            # Not yet computed this round (e.g. an intra-SCC callee on the
            # first pass) -- contributes nothing this iteration; the next
            # join pass picks it up once it has a value. Never treated as
            # poison on its own (that would make every fresh SCC poisoned
            # on iteration 0), only a genuinely unresolved callee is.
            continue
        requires |= callee_summary.requires
        transitions |= callee_summary.transitions
        acquired |= callee_summary.acquired
        released |= callee_summary.released
        escaped |= callee_summary.escaped
        if callee_summary.poisoned:
            poisoned = True
            reason = reason or f"{member} transitively poisoned via {callee}"
    return (
        frozenset(requires),
        frozenset(transitions),
        frozenset(acquired),
        frozenset(released),
        frozenset(escaped),
        poisoned,
        reason,
    )


# frob:ticket T-0976
def _singleton_summary(
    member: str,
    own_by_symref: dict[str, tuple],
    callgraph: CallGraph,
    summaries: dict[str, FunctionSummary],
) -> FunctionSummary:
    """A single-member, non-self-recursive SCC's `FunctionSummary`: one
    `_join_from_callees` call against the ALREADY-COMPUTED `summaries` (its
    callees, in bottom-up SCC order, are guaranteed done already) --
    `compute_protocol_summaries`'s non-recursive-case half."""
    own_req, own_trans, own_acq, own_rel, own_esc = own_by_symref[member]
    req, trans, acq, rel, esc, poisoned, reason = _join_from_callees(
        member,
        own_req,
        own_trans,
        own_acq,
        own_rel,
        own_esc,
        False,
        callgraph,
        summaries,
    )
    return FunctionSummary(
        symref=member,
        requires=req,
        transitions=trans,
        acquired=acq,
        released=rel,
        escaped=esc,
        poisoned=poisoned,
        poison_reason=reason,
    )


# frob:ticket T-0976
def _fixpoint_scc_summaries(
    members: list[str],
    own_by_symref: dict[str, tuple],
    callgraph: CallGraph,
    summaries: dict[str, FunctionSummary],
    max_iterations: int,
) -> tuple[dict[str, FunctionSummary], "SCCTimeout | None"]:
    """A recursive SCC's (mutual or self-recursion) `FunctionSummary`s,
    iterating the join across all `members` to a fixpoint bounded by
    `max_iterations` -- `compute_protocol_summaries`'s recursive-case
    half. Returns `(member -> summary, timeout)`, `timeout` non-`None`
    only if the join failed to converge (every member's summary is then
    poisoned)."""
    current: dict[str, FunctionSummary] = {
        m: FunctionSummary(
            symref=m,
            requires=own_by_symref[m][0],
            transitions=own_by_symref[m][1],
            acquired=own_by_symref[m][2],
            released=own_by_symref[m][3],
            escaped=own_by_symref[m][4],
        )
        for m in members
    }
    converged = False
    for _iteration in range(1, max_iterations + 1):
        next_round, changed = _one_scc_join_round(
            members, own_by_symref, callgraph, summaries, current
        )
        current = next_round
        if not changed:
            converged = True
            break

    if converged:
        return current, None
    return _poison_scc_on_timeout(current, members, max_iterations)


# frob:ticket T-0976
def _one_scc_join_round(
    members: list[str],
    own_by_symref: dict[str, tuple],
    callgraph: CallGraph,
    summaries: dict[str, FunctionSummary],
    current: dict[str, FunctionSummary],
) -> tuple[dict[str, FunctionSummary], bool]:
    """One fixpoint-iteration round over `members`: `_join_from_callees`
    against `{**summaries, **current}`, returning `(next_round, changed)`
    -- `_fixpoint_scc_summaries`'s single-round half, split from its own
    iterate-to-convergence loop."""
    combined = {**summaries, **current}
    changed = False
    next_round: dict[str, FunctionSummary] = {}
    for member in members:
        own_req, own_trans, own_acq, own_rel, own_esc = own_by_symref[member]
        req, trans, acq, rel, esc, poisoned, reason = _join_from_callees(
            member,
            own_req,
            own_trans,
            own_acq,
            own_rel,
            own_esc,
            False,
            callgraph,
            combined,
        )
        prior = current[member]
        if (
            req != prior.requires
            or trans != prior.transitions
            or acq != prior.acquired
            or rel != prior.released
            or esc != prior.escaped
            or poisoned != prior.poisoned
        ):
            changed = True
        next_round[member] = FunctionSummary(
            symref=member,
            requires=req,
            transitions=trans,
            acquired=acq,
            released=rel,
            escaped=esc,
            poisoned=poisoned,
            poison_reason=reason or prior.poison_reason,
        )
    return next_round, changed


# frob:ticket T-0976
def _poison_scc_on_timeout(
    current: dict[str, FunctionSummary], members: list[str], max_iterations: int
) -> tuple[dict[str, FunctionSummary], "SCCTimeout"]:
    """Poison every member's summary in `current` after the fixpoint
    failed to converge within `max_iterations` -- `_fixpoint_scc_
    summaries`'s non-convergence half, split from its own iterate-to-
    convergence loop."""
    _log.error(
        "T-0745: SCC %s failed to converge within %d iteration(s)",
        members,
        max_iterations,
    )
    timeout = SCCTimeout(members=tuple(members), iterations=max_iterations)
    for member in members:
        prior = current[member]
        current[member] = FunctionSummary(
            symref=member,
            requires=prior.requires,
            transitions=prior.transitions,
            poisoned=True,
            poison_reason=(
                f"SCC {members} did not converge within {max_iterations} iteration(s)"
            ),
        )
    return current, timeout


# frob:doc docs/modules/graph.md#protocol-summary-engine
# frob:ticket T-0745
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_leaf_function_summary_is_its_own_declarations  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_caller_summary_includes_callee_transitions  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_requires_and_transitions_join_across_two_hops  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_recursive_cluster_converges_to_hand_computed_fixpoint  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_self_recursive_function_converges  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_unresolved_callee_poisons_the_summary  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_poisoning_propagates_transitively_through_a_clean_caller  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_unreachable_function_is_reported_not_analyzed_never_silent  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_diamond_shaped_calls_join_without_duplication_or_loss  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_leaf_resource_declarations_populate_acquired_released_escaped  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_resource_sets_join_transitively_through_a_caller  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestProtocolSummaryEngine.test_resource_sets_join_across_a_recursive_cluster  # noqa: E501
def compute_protocol_summaries(
    callgraph: CallGraph,
    edges: Sequence[Edge],
    entrypoints: Sequence[str],
    *,
    max_iterations: int = _DEFAULT_MAX_ITERATIONS,
) -> SummaryResult:
    """Bottom-up fixpoint over `callgraph`'s SCC condensation, summarizing
    every function reachable from `entrypoints` per the T-0744 protocol
    DSL. Recursion (a multi-member SCC, or a single self-recursive
    function) is handled by iterating the join to a fixpoint (bounded by
    `max_iterations`; a monotone union/or-poison lattice over a finite
    universe always converges well under that bound in practice -- hitting
    the cap is itself the abort case the NO-FAIL-SILENT mandate wants
    surfaced, see `SummaryResult.timeouts`). A function never reached from
    any entrypoint gets no summary at all -- it is named in
    `SummaryResult.not_analyzed` instead of silently defaulting to an
    empty (falsely "clean") summary."""
    universe = _universe(callgraph, edges, entrypoints)
    reachable = _reachable(callgraph, entrypoints, universe)
    not_analyzed = tuple(sorted(universe - reachable))
    own_by_symref = {n: _own_contribution(n, edges) for n in reachable}

    sccs = _tarjan_sccs(sorted(reachable), callgraph)
    summaries: dict[str, FunctionSummary] = {}
    timeouts: list[SCCTimeout] = []

    for members in sccs:
        is_self_recursive = len(members) == 1 and members[0] in callgraph.calls.get(
            members[0], ()
        )
        if len(members) == 1 and not is_self_recursive:
            member = members[0]
            summaries[member] = _singleton_summary(
                member, own_by_symref, callgraph, summaries
            )
            continue

        # Recursive cluster (mutual recursion, or a single self-recursive
        # function): iterate the join across all members until no member's
        # value changes, bounded by max_iterations.
        current, timeout = _fixpoint_scc_summaries(
            members, own_by_symref, callgraph, summaries, max_iterations
        )
        if timeout is not None:
            timeouts.append(timeout)
        summaries.update(current)

    if not_analyzed:
        _log.warning(
            "T-0745: %d function(s) not reachable from any entrypoint: %s",
            len(not_analyzed),
            not_analyzed,
        )
    return SummaryResult(
        summaries=summaries, not_analyzed=not_analyzed, timeouts=tuple(timeouts)
    )


# =====================================================================
# T-2504: path-confinement provenance lattice, hosted on this module's
# existing SCC-ordered worklist (`_universe`/`_reachable`/`_tarjan_sccs`),
# per the T-0745 design constraint this module's own docstring records
# ("a future consumer should host its own lattice over the exact same
# SCC-ordered worklist instead of re-deriving call-graph traversal").
# REPORT-ONLY (user directive, 2026-08-18): this is a MEASUREMENT, not a
# gate -- nothing here is wired into `frob check`, and no severity is
# assigned. See docs/modules/graph.md#path-confinement-census for the
# full staging plan this measurement feeds.
# =====================================================================


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:ticket T-2504
# frob:doc docs/modules/graph.md#path-confinement-census
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl.test_absolute_literal_write_is_escaped  # noqa: E501
class ConfinementState(StrEnum):
    """The 3-value path-confinement lattice (T-2504's own spec):
    `ROOTED` -- provably derived from a sanctioned root (a `tmp_path`/
    `tmp_path_factory`/`tmpdir` fixture parameter, or `tempfile.*`) via
    only confinement-preserving operations (`/` or `os.path.join` with a
    relative literal, `.with_name`/`.with_suffix`/`.with_stem`).
    `ESCAPED` -- provably OUTSIDE any sanctioned root: an absolute string
    literal, `Path.home()`, `os.getcwd()`, `os.path.expanduser`, or an
    `os.environ` lookup feeding the path.
    `UNKNOWN` -- unprovable with this pass's own precision, OR
    transitively poisoned by a call to a private helper this pass could
    not itself prove `ROOTED`/`ESCAPED` for. Never rendered as a pass:
    a census consumer must treat `UNKNOWN` exactly like
    `FunctionSummary.poisoned` in the protocol engine above -- an open
    question, not a clean bill of health."""

    ROOTED = "rooted"
    ESCAPED = "escaped"
    UNKNOWN = "unknown"


# Parameter names this pass accepts as sanctioned roots without any
# further proof -- the pytest `tmp_path`/`tmp_path_factory`/`tmpdir`
# fixtures are the only ones a test file gets for free; anything else
# (a project fixture) must itself be PROVEN confinement-preserving by a
# separate pass before it could be added here (T-2504's own ticket body:
# "any project-declared fixture the engine has itself proven
# confinement-preserving" -- none exist yet, so this stays exactly the
# pytest-builtin set for this first, report-only pass).
_SANCTIONED_ROOT_PARAMS = frozenset({"tmp_path", "tmp_path_factory", "tmpdir"})

# Dotted call names that always produce a value rooted under a sanctioned
# temp directory, regardless of arguments.
_ROOTING_CALLS = frozenset(
    {
        "tempfile.mkdtemp",
        "tempfile.mkstemp",
        "tempfile.gettempdir",
        "tempfile.TemporaryDirectory",
        "tempfile.NamedTemporaryFile",
    }
)

# Dotted call names that always escape confinement, regardless of
# arguments -- the ESCAPED half of the lattice's "provably outside" set.
_ESCAPING_CALLS = frozenset(
    {
        "Path.home",
        "os.getcwd",
        "os.path.expanduser",
        "pathlib.Path.home",
    }
)

# `.attr` accesses (no call) that always escape -- `os.environ[...]`/
# `os.environ.get(...)` are handled separately (subscript/call on this
# base), this set is for a bare escaping attribute reference used as a
# path directly.
_ESCAPING_ATTRS = frozenset({"os.environ"})

# Path-method calls that preserve confinement of their `self` receiver
# (the confinement-preserving half of T-2504's own op list).
_CONFINEMENT_PRESERVING_METHODS = frozenset({"with_name", "with_suffix", "with_stem"})

# `fs.write`-shaped call sites this pass recognizes -- a conservative,
# report-only subset (T-2504's own scope: "the ~352 fs.write sites in
# tests/"). `(dotted_or_method_name, path_arg_position)`: for a METHOD
# call (`X.write_text(...)`), `path_arg_position` is `None` and the
# receiver `X` itself is the path under test; for a free FUNCTION call
# (`open(X, "w")`), it is the 0-based positional index of the path
# argument.
_FS_WRITE_METHODS = frozenset({"write_text", "write_bytes"})
_FS_WRITE_CALLS: Mapping[str, int] = {
    "open": 0,
    "Path.open": 0,
}


@dataclass(frozen=True)
class _Pending:
    """A local variable (or a function's own return value) whose
    confinement state depends on a call to a PRIVATE callee this
    single-function pass cannot itself resolve -- `compute_confinement_
    summaries` finalizes it once that callee's own summary is available
    on the bottom-up SCC worklist, exactly mirroring how `_join_from_
    callees` above defers an intra-SCC callee's not-yet-computed value.
    `arg_state` is the ALREADY-resolved state of the argument passed to
    `callee` at this call site (resolvable immediately, since it only
    depends on statements earlier in the same function)."""

    callee: str
    arg_state: ConfinementState


@dataclass(frozen=True)
class _ParamRef:
    """A local variable (or a function's own return value) that is
    exactly this function's OWN parameter `name`, unmodified apart from
    confinement-PRESERVING operations (T-2504's `_write_fixture(tmp:
    Path)` example: `tmp / "x"` is `_ParamRef("tmp")`, not a concrete
    state) -- its real confinement depends on whatever the CALLER passes
    for `name`, which only `compute_confinement_summaries`'s function-
    level finalization (not this single-function pass) can resolve: a
    `_ParamRef` used directly as an `fs.write` site's own target resolves
    UNKNOWN (this pass has no interprocedural argument values at a call
    site to check what was actually passed); a `_ParamRef` as the
    function's OWN return value instead becomes `FunctionConfinement.
    return_depends_on_param`, the exact "param0 confined => result
    confined" contract the ticket names."""

    name: str


_LocalState = ConfinementState | _Pending | _ParamRef


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:doc docs/modules/graph.md#path-confinement-census
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl.test_absolute_literal_write_is_escaped  # noqa: E501
class FsWriteSite(BaseModel):
    """One recognized `fs.write`-shaped call site (T-2504): `state` is
    this pass's FINAL verdict (after cross-function resolution), and
    `poison_source` names the private callee responsible for an
    `UNKNOWN` verdict when the site's own local reasoning was blocked on
    an unresolved/unprovable helper call, `None` for a site that was
    already directly unprovable (an unrecognized construct) with no
    single attributable helper."""

    model_config = ConfigDict(frozen=True)

    symref: str
    lineno: int
    path_repr: str
    state: ConfinementState
    poison_source: str | None = None


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:doc docs/modules/graph.md#path-confinement-census
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticeHelperPropagation.test_helper_return_value_confinement_propagates_to_caller_site  # noqa: E501
class FunctionConfinement(BaseModel):
    """One function's confinement contribution (T-2504): whether its
    RETURN value's confinement is a fixed `return_always` state
    independent of its own parameters, or tracks one of its own
    parameters 1:1 (`return_depends_on_param`, the "`param0` confined =>
    result confined" shape the ticket names) -- at most one of the two is
    set; both `None` means this function's return value is not a
    path-shaped expression this pass could classify at all (callers that
    reference its result default to `UNKNOWN`, never a guessed pass).
    `sites` are this function's OWN `fs.write` call sites (not its
    callees') with `state` already finalized against every callee this
    pass could resolve."""

    model_config = ConfigDict(frozen=True)

    symref: str
    return_depends_on_param: str | None = None
    return_always: ConfinementState | None = None
    sites: tuple[FsWriteSite, ...] = ()


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:doc docs/modules/graph.md#path-confinement-census
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl.test_ordinary_tmp_path_write_is_rooted_not_escaped  # noqa: E501
class ConfinementCensusResult(BaseModel):
    """The full census: every `fs.write` site this pass recognized
    across every function `compute_confinement_summaries` was asked to
    cover, plus a poison-source breakdown (T-2504's explicitly-requested
    "which helpers are the biggest poison sources" list) and
    `not_analyzed` for the same NO-FAIL-SILENT reason `SummaryResult`
    carries it: a function outside the reachable set never silently
    contributes zero sites."""

    model_config = ConfigDict(frozen=True)

    sites: tuple[FsWriteSite, ...] = ()
    not_analyzed: tuple[str, ...] = ()
    poison_sources: Mapping[str, int] = {}

    # frob:doc docs/modules/graph.md#path-confinement-census
    @property
    def counts(self) -> Mapping[str, int]:
        """`{ROOTED: n, ESCAPED: n, UNKNOWN: n}` over `self.sites` -- the
        exact PROVEN/ESCAPED/UNKNOWN census number this ticket's first
        deliverable publishes."""
        out = {state.value: 0 for state in ConfinementState}
        for site in self.sites:
            out[site.state.value] += 1
        return out


def _dotted_name(node: ast.expr) -> str | None:
    """`a.b.c` (or a bare `a`) rendered as a dotted string, or `None` if
    `node` is not a plain attribute/name chain (a call result, subscript,
    etc. is not a "dotted name" -- callers must handle those shapes
    separately)."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _is_relative_safe_literal(node: ast.expr) -> bool:
    """`True` iff `node` is a string constant that is safe to join onto a
    confined base: not absolute (does not start with `/`), and does not
    contain a `..` path-traversal segment. Anything else (a non-constant,
    an f-string, a variable) is NOT safe by this check alone -- confinement
    of a variable component is resolved separately via `_classify_expr`."""
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
        return False
    value = node.value
    if value.startswith("/") or value.startswith("\\"):
        return False
    return ".." not in Path(value).parts


def _classify_expr(
    expr: ast.expr, locals_: Mapping[str, _LocalState], params: frozenset[str]
) -> _LocalState:
    """Classify one path-shaped expression's confinement (T-2504's own
    per-op rules): a `Name` resolves through `locals_`/`params`; a `/`
    `BinOp` or `os.path.join(...)`/`.with_name(...)`-shaped `Call`
    resolves via its confined operand IF every other operand is a safe
    relative literal (`_is_relative_safe_literal`); an absolute literal,
    `Path.home()`/`os.getcwd()`/`os.environ[...]`, or the repo-root-
    looking `Path(__file__).parent...` chain resolves `ESCAPED`; a call
    to an unresolved/unrecognized callable resolves `UNKNOWN` (or a
    `_Pending` marker if it is a call to a private callee this SINGLE-
    function pass cannot itself resolve, deferred to `compute_
    confinement_summaries`'s cross-function join). Anything else this
    function does not recognize is `UNKNOWN` -- the conservative default
    NO-FAIL-SILENT requires: an unrecognized construct is never guessed
    `ROOTED`."""
    if isinstance(expr, ast.Name):
        if expr.id in params and expr.id in _SANCTIONED_ROOT_PARAMS:
            return ConfinementState.ROOTED
        if expr.id in locals_:
            return locals_[expr.id]
        if expr.id in params:
            # A parameter that is NOT a sanctioned root name -- e.g. a
            # plain `path: Path` argument. Symbolic: its real confinement
            # depends on what the CALLER passes (see `_ParamRef`'s own
            # docstring); a direct USE as a site target still resolves
            # UNKNOWN (`_resolve_state` below), only a RETURN of it
            # becomes a real param-dependent function summary.
            return _ParamRef(expr.id)
        return ConfinementState.UNKNOWN

    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return (
            ConfinementState.ESCAPED
            if expr.value.startswith(("/", "\\"))
            else ConfinementState.UNKNOWN
        )

    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
        left = _classify_expr(expr.left, locals_, params)
        if _is_relative_safe_literal(expr.right):
            return left
        # An unrecognized right operand can only ever narrow (never
        # widen) the left side's confinement: an already-ESCAPED base
        # stays ESCAPED regardless of what is joined onto it, anything
        # else is UNKNOWN rather than guessed ROOTED.
        return left if left is ConfinementState.ESCAPED else ConfinementState.UNKNOWN

    if isinstance(expr, ast.Call):
        return _classify_call(expr, locals_, params)

    if isinstance(expr, ast.Subscript):
        base = _dotted_name(expr.value)
        if base == "os.environ":
            return ConfinementState.ESCAPED
        return ConfinementState.UNKNOWN

    return ConfinementState.UNKNOWN


def _classify_call(
    expr: ast.Call, locals_: Mapping[str, _LocalState], params: frozenset[str]
) -> _LocalState:
    """`_classify_expr`'s `ast.Call` branch, split out to keep that
    function under ARCH001's length threshold (T-2504): dotted stdlib
    calls (`tempfile.*`/`Path.home`/`os.path.join`/`os.environ.get`/
    `Path(...)`/`.with_name`-shaped) resolve via the module-level lookup
    tables; a call to a name that LOOKS like a private helper (Python's
    leading-underscore convention) defers to cross-function resolution
    via a `_Pending` marker instead of guessing -- the actual callee
    symref is resolved later by `_scan_function_facts`'s caller, which
    has the enclosing module's qualname context this pure classifier
    does not."""
    dotted = _dotted_name(expr.func)
    if dotted is not None:
        if dotted in _ROOTING_CALLS:
            return ConfinementState.ROOTED
        if dotted in _ESCAPING_CALLS:
            return ConfinementState.ESCAPED
        if dotted == "os.path.join" and expr.args:
            base = _classify_expr(expr.args[0], locals_, params)
            if all(_is_relative_safe_literal(a) for a in expr.args[1:]):
                return base
            return ConfinementState.UNKNOWN
        if dotted == "os.environ.get":
            return ConfinementState.ESCAPED
        if dotted == "Path" and expr.args:
            return _classify_expr(expr.args[0], locals_, params)
        last = dotted.rsplit(".", 1)[-1]
        if last in _CONFINEMENT_PRESERVING_METHODS and isinstance(
            expr.func, ast.Attribute
        ):
            return _classify_expr(expr.func.value, locals_, params)
    if isinstance(expr.func, ast.Name) and expr.func.id.startswith("_"):
        arg_state: _LocalState = ConfinementState.UNKNOWN
        if expr.args:
            arg_state = _classify_expr(expr.args[0], locals_, params)
        if isinstance(arg_state, ConfinementState):
            return _Pending(callee=f"?private:{expr.func.id}", arg_state=arg_state)
    return ConfinementState.UNKNOWN


def _fs_write_site(
    call: ast.Call, locals_: Mapping[str, _LocalState], params: frozenset[str]
) -> tuple[str, _LocalState] | None:
    """If `call` is a recognized `fs.write`-shaped call (T-2504's own
    conservative subset: `open(path, "w"/"wb"/"a"/...)`, `Path.write_
    text`/`write_bytes`), return `(path_repr, state)` for its path
    argument/receiver; `None` if `call` is not one of the recognized
    shapes at all (not a site this census counts, not even as UNKNOWN --
    an unrecognized CALL SHAPE is out of scope, distinct from a
    recognized site whose PATH is unprovable)."""
    if isinstance(call.func, ast.Attribute) and call.func.attr in _FS_WRITE_METHODS:
        receiver = call.func.value
        return ast.unparse(receiver), _classify_expr(receiver, locals_, params)
    if isinstance(call.func, ast.Name) and call.func.id == "open":
        mode: str | None = None
        if len(call.args) >= 2:
            mode_node = call.args[1]
            if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
                mode = mode_node.value
        for kw in call.keywords:
            if (
                kw.arg == "mode"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ):
                mode = kw.value.value
        if mode is not None and not any(c in mode for c in "wax+"):
            return None
        if not call.args:
            return None
        return ast.unparse(call.args[0]), _classify_expr(call.args[0], locals_, params)
    return None


@dataclass(frozen=True)
class _RawFuncFacts:
    """One function's OWN facts (T-2504), before cross-function
    resolution: its `fs.write` sites (path repr + locally-resolved state,
    possibly `_Pending` on a private callee) and its own return
    expression's state (same shape) -- `compute_confinement_summaries`
    finalizes both against the real call graph's callee summaries."""

    symref: str
    sites: tuple[tuple[int, str, _LocalState], ...]
    return_state: _LocalState | None


def _qualname_stack(node: ast.AST, stack: tuple[str, ...] = ()) -> None:
    """Unused placeholder kept out of `__all__` -- see `_iter_functions`
    for the real (stack-threading) qualname walk; this name is not
    referenced elsewhere and exists only so a future nested-class
    extension has an obvious anchor point. T-2504 does not need nested-
    class qualnames for `tests/**` (pytest test classes are never
    nested), so `_iter_functions` below only threads ONE level of class
    nesting, matching `frob.lang._walk_python`'s own stack convention
    (`".".join((*stack, name))`) without needing the general case yet."""
    raise NotImplementedError


def _iter_functions(
    tree: ast.Module,
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """`(qualname, node)` for every top-level function and every method of
    every top-level class in `tree` -- `path::qualname` matches `frob.lang.
    _walk_python`'s own `".".join((*stack, name))` convention (T-2504:
    same symref shape `build_call_graph` produces, so this pass's own
    symrefs line up with the real call graph's without needing a second
    resolution step). Nested functions/classes are not walked (out of
    scope for `tests/**`'s flat fixture/helper shape)."""
    out: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((f"{node.name}.{item.name}", item))
    return out


def _scan_function_facts(
    qualname: str, func: ast.FunctionDef | ast.AsyncFunctionDef
) -> _RawFuncFacts:
    """`func`'s own `_RawFuncFacts` (T-2504): a SINGLE linear forward pass
    over `func.body`'s TOP-LEVEL statements only -- `Assign`/`AnnAssign`
    to a bare `Name` update the local-state map, an `fs.write`-shaped
    `Expr`/`Assign` call records a site, `return` records the function's
    own return state. A statement NESTED inside an `if`/`for`/`while`/
    `with`/`try` block is deliberately NOT tracked into the local-state
    map (this pass has no real control-flow/branch-join logic) -- an
    `fs.write` call site found INSIDE such a block still gets recorded,
    but resolved only against whatever the top-level map already holds
    at that point (locals reassigned inside the block are invisible to
    it), which biases the verdict toward `UNKNOWN` rather than ever
    fabricating a false `ROOTED`/`ESCAPED` from an assignment this pass
    did not actually see. This conservative, precision-over-recall
    posture is a DELIBERATE, disclosed limitation of this first,
    report-only pass -- see docs/modules/graph.md#path-confinement-census
    for the staging note this feeds."""
    params = frozenset(
        a.arg
        for a in (*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs)
    )
    locals_: dict[str, _LocalState] = {}
    sites: list[tuple[int, str, _LocalState]] = []
    return_state: _LocalState | None = None

    def visit_call_exprs(node: ast.AST) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                site = _fs_write_site(child, locals_, params)
                if site is not None:
                    path_repr, state = site
                    sites.append((child.lineno, path_repr, state))

    for stmt in func.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name):
                locals_[target.id] = _classify_expr(stmt.value, locals_, params)
            visit_call_exprs(stmt.value)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if isinstance(stmt.target, ast.Name):
                locals_[stmt.target.id] = _classify_expr(stmt.value, locals_, params)
            visit_call_exprs(stmt.value)
        elif isinstance(stmt, ast.Return) and stmt.value is not None:
            return_state = _classify_expr(stmt.value, locals_, params)
            visit_call_exprs(stmt.value)
        else:
            visit_call_exprs(stmt)

    return _RawFuncFacts(
        symref=qualname, sites=tuple(sites), return_state=return_state
    )


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl.test_absolute_literal_write_is_escaped  # noqa: E501
def scan_confinement_facts(
    root: Path, paths: Sequence[str]
) -> dict[str, _RawFuncFacts]:
    """Read and `ast.parse` every `.py` file in `paths` (relative to
    `root`), returning `{symref: _RawFuncFacts}` over every top-level
    function/method found (T-2504). THIS function does the filesystem
    walk `compute_confinement_summaries` deliberately does not (matching
    this module's existing `compute_protocol_summaries`'s offline-only
    posture -- see the module docstring) -- a parse failure on one file
    is logged and that file's functions are simply absent from the
    result (never a silent empty summary attributed to a real symref;
    `compute_confinement_summaries`'s own `not_analyzed` reporting is
    what a caller should use to notice a gap, by omitting the affected
    files' functions from BOTH the returned facts and the `entrypoints`/
    universe it builds its `CallGraph` from)."""
    out: dict[str, _RawFuncFacts] = {}
    for rel in paths:
        if not rel.endswith(".py"):
            continue
        file_path = root / rel
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel)
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            _log.warning("T-2504: confinement scan skipped %s (%s)", rel, exc)
            continue
        for qualname, func in _iter_functions(tree):
            symref = f"{rel}::{qualname}"
            out[symref] = _scan_function_facts(qualname, func)
    return out


def _resolve_callee_symref(
    caller_symref: str, short_name: str, facts: Mapping[str, _RawFuncFacts]
) -> str:
    """Best-effort resolution of `short_name` (an identifier used at a
    call site that LOOKS like a call to a private helper, per Python's
    leading-underscore convention) to a real symref key of `facts` --
    prefers a candidate in the SAME file as `caller_symref`, matching
    `frob.graph.callgraph.build_call_graph`'s own same-file-preferred
    resolution posture; falls back to any matching candidate repo-wide,
    or `UNRESOLVED_CALLEE` (T-0809's shared sentinel) if none exists,
    which `compute_confinement_summaries` then poisons exactly like the
    protocol engine above poisons a genuinely unresolved call."""
    caller_path = caller_symref.split("::", 1)[0]
    candidates = [
        s
        for s in facts
        if s.rsplit("::", 1)[-1] == short_name
        or s.rsplit("::", 1)[-1].endswith(f".{short_name}")
    ]
    same_file = [c for c in candidates if c.split("::", 1)[0] == caller_path]
    if same_file:
        return same_file[0]
    if candidates:
        return candidates[0]
    return UNRESOLVED_CALLEE


def _resolve_pending_placeholders(
    facts: Mapping[str, _RawFuncFacts],
) -> dict[str, _RawFuncFacts]:
    """`facts` with every `_Pending.callee` placeholder (`"?private:name"`,
    written by `_classify_expr`, which has no cross-file symref context of
    its own) rewritten to a real resolved symref via `_resolve_callee_
    symref` -- a single, explicit resolution pass so both the synthetic
    `CallGraph` this module builds AND `_resolve_state`'s `summaries`
    lookup key off the SAME resolved symref, never the raw placeholder."""

    def resolve_one(symref: str, state: _LocalState) -> _LocalState:
        if isinstance(state, _Pending) and state.callee.startswith("?private:"):
            short_name = state.callee.removeprefix("?private:")
            return _Pending(
                callee=_resolve_callee_symref(symref, short_name, facts),
                arg_state=state.arg_state,
            )
        return state

    out: dict[str, _RawFuncFacts] = {}
    for symref, raw in facts.items():
        sites = tuple(
            (lineno, path_repr, resolve_one(symref, state))
            for lineno, path_repr, state in raw.sites
        )
        return_state = (
            resolve_one(symref, raw.return_state)
            if raw.return_state is not None
            else None
        )
        out[symref] = _RawFuncFacts(symref=symref, sites=sites, return_state=return_state)
    return out


def _build_confinement_callgraph(facts: Mapping[str, _RawFuncFacts]) -> CallGraph:
    """The synthetic `CallGraph` this pass's own private-callee edges
    describe (T-2504) -- built from resolved `_Pending` markers so
    `compute_confinement_summaries` can host its fixpoint on the SAME
    `_universe`/`_reachable`/`_tarjan_sccs` worklist machinery
    `compute_protocol_summaries` above already uses, per the T-0745
    design constraint. Call `_resolve_pending_placeholders` on `facts`
    FIRST -- this function assumes every `_Pending.callee` is already a
    real symref (or `UNRESOLVED_CALLEE`), not a `"?private:"` placeholder."""
    calls: dict[str, tuple[str, ...]] = {}
    for symref, raw in facts.items():
        callees: list[str] = []
        for _lineno, _repr, state in raw.sites:
            if isinstance(state, _Pending):
                callees.append(state.callee)
        if isinstance(raw.return_state, _Pending):
            callees.append(raw.return_state.callee)
        calls[symref] = tuple(callees)
    return CallGraph(calls=calls)


def _resolve_state(
    state: _LocalState, summaries: Mapping[str, FunctionConfinement]
) -> tuple[ConfinementState, str | None]:
    """`state` finalized against already-computed callee `summaries`
    (T-2504): a concrete `ConfinementState` passes through unchanged; a
    `_ParamRef` (a site referencing this function's OWN unproven
    parameter directly) resolves `UNKNOWN` with no attributable poison
    source (this pass's own precision limit, not a specific callee's
    fault); a `_Pending` resolves via its callee's `FunctionConfinement`
    -- `return_always` if the callee's return is param-independent,
    `return_depends_on_param` if the callee is the "param confined =>
    result confined" shape (the call's own already-resolved `arg_state`
    IS that param's value, so it becomes the final state directly,
    single-positional-argument heuristic disclosed in `_Pending`'s own
    docstring), `UNKNOWN` with the callee's symref as `poison_source`
    if the callee itself is unresolved/not-yet-summarized (an SCC
    member still mid-fixpoint, or a genuinely unresolved private call)."""
    if isinstance(state, ConfinementState):
        return state, None
    if isinstance(state, _ParamRef):
        return ConfinementState.UNKNOWN, None
    callee_summary = summaries.get(state.callee)
    if callee_summary is None:
        return ConfinementState.UNKNOWN, state.callee
    if callee_summary.return_always is not None:
        poison = state.callee if callee_summary.return_always is ConfinementState.UNKNOWN else None
        return callee_summary.return_always, poison
    if callee_summary.return_depends_on_param is not None:
        return state.arg_state, None
    return ConfinementState.UNKNOWN, state.callee


def _finalize_function(
    raw: _RawFuncFacts, summaries: Mapping[str, FunctionConfinement]
) -> FunctionConfinement:
    """`raw`'s own facts finalized into a real `FunctionConfinement`
    against already-computed `summaries` -- `compute_confinement_
    summaries`'s per-function finalization step, shared by both the
    singleton and recursive-SCC branches (mirroring `_singleton_summary`/
    `_fixpoint_scc_summaries`'s shared `_join_from_callees` above)."""
    sites = tuple(
        FsWriteSite(
            symref=raw.symref,
            lineno=lineno,
            path_repr=path_repr,
            state=(resolved := _resolve_state(state, summaries))[0],
            poison_source=resolved[1],
        )
        for lineno, path_repr, state in raw.sites
    )
    return_depends_on_param: str | None = None
    return_always: ConfinementState | None = None
    if isinstance(raw.return_state, _ParamRef):
        return_depends_on_param = raw.return_state.name
    elif raw.return_state is not None:
        return_always, _poison = _resolve_state(raw.return_state, summaries)
    return FunctionConfinement(
        symref=raw.symref,
        return_depends_on_param=return_depends_on_param,
        return_always=return_always,
        sites=sites,
    )


def _fixpoint_confinement_scc(
    members: list[str],
    resolved_facts: Mapping[str, _RawFuncFacts],
    summaries: Mapping[str, FunctionConfinement],
) -> dict[str, FunctionConfinement]:
    """One recursive cluster's (mutual/self-recursive private helpers)
    `FunctionConfinement`s, iterating the join to a fixpoint -- `compute_
    confinement_summaries`'s recursive-case half, split out to keep that
    function under ARCH001's length threshold (T-2504). Bounded the same
    way `_fixpoint_scc_summaries` bounds the protocol engine's own
    recursive case; non-convergence poisons every member `UNKNOWN`
    rather than reporting a partial result."""
    current = {
        m: FunctionConfinement(symref=m) for m in members if m in resolved_facts
    }
    for _iteration in range(_DEFAULT_MAX_ITERATIONS):
        combined = {**summaries, **current}
        next_round = {
            m: _finalize_function(resolved_facts[m], combined) for m in current
        }
        if next_round == current:
            return next_round
        current = next_round
    return {
        m: FunctionConfinement(
            symref=m,
            sites=tuple(
                s.model_copy(update={"state": ConfinementState.UNKNOWN})
                for s in current[m].sites
            ),
        )
        for m in current
    }


def _tally_poison_sources(sites: Sequence[FsWriteSite]) -> dict[str, int]:
    """`{callee_symref: count}` over every `UNKNOWN` site in `sites` that
    has an attributable `poison_source` -- `compute_confinement_
    summaries`'s "which helpers are the biggest poison sources"
    breakdown, split out to keep that function under ARCH001's length
    threshold (T-2504)."""
    poison_sources: dict[str, int] = {}
    for site in sites:
        if site.state is ConfinementState.UNKNOWN and site.poison_source is not None:
            poison_sources[site.poison_source] = (
                poison_sources.get(site.poison_source, 0) + 1
            )
    return poison_sources


# frob:doc docs/modules/graph.md#path-confinement-census
# frob:ticket T-2504
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticeHelperPropagation.test_helper_return_value_confinement_propagates_to_caller_site  # noqa: E501
# frob:tests tests/unit/test_confinement_lattice.py::TestConfinementLatticeUnknown.test_unresolved_private_helper_call_poisons_to_unknown  # noqa: E501
def compute_confinement_summaries(
    facts: Mapping[str, _RawFuncFacts], entrypoints: Sequence[str]
) -> ConfinementCensusResult:
    """Bottom-up fixpoint over the path-confinement lattice (T-2504),
    hosted on THIS module's existing `_universe`/`_reachable`/`_tarjan_
    sccs` SCC-ordered worklist -- the exact call-graph traversal
    `compute_protocol_summaries` above already performs, reused rather
    than re-derived (T-0745's design constraint). `facts` is `scan_
    confinement_facts`'s pure output (this function itself does no
    filesystem I/O, matching the module's existing offline posture);
    `entrypoints` is every symref whose `fs.write` sites should be
    counted even if nothing in `facts` calls it (typically every test
    function -- pytest itself is the entrypoint, not a call graph edge).

    A recursive SCC (mutual/self-recursive private helpers) iterates the
    same join to a small fixed-point bound as `compute_protocol_
    summaries`'s recursive case; non-convergence poisons every member's
    sites `UNKNOWN` rather than reporting a partial result, the same
    NO-FAIL-SILENT posture that engine already holds."""
    resolved_facts = _resolve_pending_placeholders(facts)
    callgraph = _build_confinement_callgraph(resolved_facts)
    universe = set(resolved_facts) | set(entrypoints)
    reachable = _reachable(callgraph, entrypoints, universe)
    not_analyzed = tuple(sorted(universe - reachable))

    sccs = _tarjan_sccs(sorted(reachable), callgraph)
    summaries: dict[str, FunctionConfinement] = {}
    for members in sccs:
        is_self_recursive = len(members) == 1 and members[0] in callgraph.calls.get(
            members[0], ()
        )
        if len(members) == 1 and not is_self_recursive:
            member = members[0]
            raw = resolved_facts.get(member)
            summaries[member] = (
                _finalize_function(raw, summaries)
                if raw is not None
                else FunctionConfinement(symref=member)
            )
            continue
        summaries.update(
            _fixpoint_confinement_scc(members, resolved_facts, summaries)
        )

    all_sites = tuple(
        site for symref in sorted(summaries) for site in summaries[symref].sites
    )
    poison_sources = _tally_poison_sources(all_sites)

    if not_analyzed:
        _log.warning(
            "T-2504: %d function(s) not reachable from any entrypoint: %s",
            len(not_analyzed),
            not_analyzed,
        )
    return ConfinementCensusResult(
        sites=all_sites,
        not_analyzed=not_analyzed,
        poison_sources=poison_sources,
    )
