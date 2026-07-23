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

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from frob.graph._models import Edge, EdgeKind
from frob.graph.callgraph import CallGraph
from frob.logging import get_logger

__all__ = [
    "UNRESOLVED_CALLEE",
    "FunctionSummary",
    "SCCTimeout",
    "SummaryResult",
    "compute_protocol_summaries",
]

_log = get_logger(__name__)

# frob:doc docs/modules/graph.md#protocol-summary-engine
# A sentinel callee symref a caller wires into `CallGraph.calls` to mean
# "this call site could not be bound to a real callee" (e.g. a dynamic
# dispatch, an unresolved import, a T-0339-family resolver miss). The
# engine treats ANY edge pointing at this exact string as an unresolvable
# callee -- see the module docstring's NO-FAIL-SILENT clause.
UNRESOLVED_CALLEE = "?unresolved"

_DEFAULT_MAX_ITERATIONS = 100


def _own_contribution(
    symref: str, edges: Sequence[Edge]
) -> tuple[frozenset[str], frozenset[str]]:
    """`(requires, transitions)` string-sets this `symref` declares directly.

    `requires` entries render as `"proto:state"`, `transitions` entries as
    `"proto:from->to"` -- both are plain strings (not nested models) so a
    lattice join is just set union, and a hand-computed expected value in
    a test is a one-line set literal."""
    requires: set[str] = set()
    transitions: set[str] = set()
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
    return frozenset(requires), frozenset(transitions)


# frob:doc docs/modules/graph.md#protocol-summary-engine
class FunctionSummary(BaseModel):
    """One function's fixpoint-computed protocol contribution.

    `requires`/`transitions` are the transitive union over everything this
    function (directly or indirectly) calls, plus its own declarations.
    `poisoned` is `True` the moment any callee in the transitive closure is
    `UNRESOLVED_CALLEE` or itself poisoned -- `requires`/`transitions` are
    still populated with whatever WAS resolved (best-effort), but a
    consumer must treat a poisoned summary as untrustworthy, per the
    NO-FAIL-SILENT mandate (an ERROR downstream, never silence)."""

    model_config = ConfigDict(frozen=True)

    symref: str
    requires: frozenset[str] = frozenset()
    transitions: frozenset[str] = frozenset()
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
        if e.kind in (EdgeKind.REQUIRES, EdgeKind.TRANSITION):
            nodes.add(e.src)
    return nodes


def _reachable(
    callgraph: CallGraph, entrypoints: Sequence[str], universe: set[str]
) -> set[str]:
    """BFS forward closure (caller -> callee) from `entrypoints`, restricted
    to `universe` -- a function no entrypoint ever calls, transitively, is
    NOT reachable and must not receive a summary (`not_analyzed` instead)."""
    seen: set[str] = set()
    stack = [n for n in entrypoints if n in universe]
    seen.update(stack)
    while stack:
        node = stack.pop()
        for callee in callgraph.calls.get(node, ()):
            if callee == UNRESOLVED_CALLEE or callee in seen:
                continue
            seen.add(callee)
            stack.append(callee)
    return seen


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
                sccs.append(sorted(scc))
    return sccs


def _join_from_callees(
    member: str,
    own_req: frozenset[str],
    own_trans: frozenset[str],
    own_poisoned: bool,
    callgraph: CallGraph,
    lookup: Mapping[str, FunctionSummary],
) -> tuple[frozenset[str], frozenset[str], bool, str | None]:
    """One join step for `member`: its own declarations unioned with every
    callee's CURRENT summary in `lookup` (cross-SCC callees are final by
    the time this runs; intra-SCC callees are this round's in-progress
    values) -- the lattice-join core both the single-node and recursive-
    SCC branches of `compute_protocol_summaries` share."""
    requires = set(own_req)
    transitions = set(own_trans)
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
        if callee_summary.poisoned:
            poisoned = True
            reason = reason or f"{member} transitively poisoned via {callee}"
    return frozenset(requires), frozenset(transitions), poisoned, reason


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
            own_req, own_trans = own_by_symref[member]
            req, trans, poisoned, reason = _join_from_callees(
                member, own_req, own_trans, False, callgraph, summaries
            )
            summaries[member] = FunctionSummary(
                symref=member,
                requires=req,
                transitions=trans,
                poisoned=poisoned,
                poison_reason=reason,
            )
            continue

        # Recursive cluster (mutual recursion, or a single self-recursive
        # function): iterate the join across all members until no member's
        # value changes, bounded by max_iterations.
        current: dict[str, FunctionSummary] = {
            m: FunctionSummary(
                symref=m, requires=own_by_symref[m][0], transitions=own_by_symref[m][1]
            )
            for m in members
        }
        converged = False
        for iteration in range(1, max_iterations + 1):
            combined = {**summaries, **current}
            changed = False
            next_round: dict[str, FunctionSummary] = {}
            for member in members:
                own_req, own_trans = own_by_symref[member]
                req, trans, poisoned, reason = _join_from_callees(
                    member, own_req, own_trans, False, callgraph, combined
                )
                prior = current[member]
                if (
                    req != prior.requires
                    or trans != prior.transitions
                    or poisoned != prior.poisoned
                ):
                    changed = True
                next_round[member] = FunctionSummary(
                    symref=member,
                    requires=req,
                    transitions=trans,
                    poisoned=poisoned,
                    poison_reason=reason or prior.poison_reason,
                )
            current = next_round
            if not changed:
                converged = True
                break
        if not converged:
            _log.error(
                "T-0745: SCC %s failed to converge within %d iteration(s)",
                members,
                max_iterations,
            )
            timeouts.append(
                SCCTimeout(members=tuple(members), iterations=max_iterations)
            )
            for member in members:
                prior = current[member]
                current[member] = FunctionSummary(
                    symref=member,
                    requires=prior.requires,
                    transitions=prior.transitions,
                    poisoned=True,
                    poison_reason=(
                        f"SCC {members} did not converge within "
                        f"{max_iterations} iteration(s)"
                    ),
                )
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
