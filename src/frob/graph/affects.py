"""The doc-drift digest-graph query (docs/modules/graph.md#affects,
T-0325): "if X's digest changed, exactly WHICH documentation and WHICH
other code must be reviewed/updated" -- warm, from the already-built
`GraphSnapshot`, without running a single test. This is the project's
north-star query (CLAUDE.md): a static type-checker for obligations,
answered from edges alone.

Built entirely on `frob.graph`'s existing `edges_from`/`edges_to` -- no new
storage, no new build pass. `frob_doc_for` (T-0177-adjacent) already answers
the ONE-HOP doc question for a single symbol; `affects` extends that to the
TRANSITIVE case a contract change actually has: a signature change to `X`
also invalidates the docs/tests of every symbol that `frob:uses-contract X`
(directly or through a chain of such dependents), not just `X`'s own direct
doc/test edges.
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel, ConfigDict

from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

# Bounds mirror `frob.graph.callgraph.closure`'s posture (INV-014): a
# best-effort triage aid over a real-world graph must be depth-limited and
# node-capped, or a densely cross-referenced module turns one query into an
# unbounded walk.
_DEFAULT_MAX_DEPTH = 8
_DEFAULT_MAX_NODES = 500


# frob:doc docs/modules/graph.md#affects
class AffectedSet(BaseModel):
    """The full answer to "what must update when `root` changes": every
    symbol transitively dependent on `root`'s contract (`uses-contract`
    chain), plus the doc anchors and tests that cover `root` and each of
    those dependents. `truncated=True` means `max_depth`/`max_nodes` cut the
    dependent walk short -- the doc/test sets are still exact for every node
    that WAS visited, but there may be more dependents beyond the bound."""

    model_config = ConfigDict(frozen=True)

    root: str
    dependents: tuple[str, ...]
    docs: tuple[str, ...]
    tests: tuple[str, ...]
    truncated: bool


def _doc_targets_for(snapshot: GraphSnapshot, ref: str) -> set[str]:
    """Doc anchors obligated by `ref`: its own `frob:doc` targets, plus any
    markdown `frob:describes` anchor pointing back at it -- the same two
    edge directions `frob_doc_for` reads, folded into one set here since the
    caller only needs "is there a doc obligation", not which direction."""
    targets = {
        edge.target
        for edge in snapshot.edges
        if edge.src == ref and edge.kind == EdgeKind.DOC
    }
    describers = {
        edge.src
        for edge in snapshot.edges
        if edge.target == ref and edge.kind == EdgeKind.DESCRIBES
    }
    return targets | describers


def _test_refs_for(snapshot: GraphSnapshot, ref: str) -> set[str]:
    """Test symrefs whose `frob:tests` directive names `ref`."""
    return {
        edge.src
        for edge in snapshot.edges
        if edge.target == ref and edge.kind == EdgeKind.TESTS
    }


def _dependents_of(snapshot: GraphSnapshot, ref: str) -> set[str]:
    """Direct `frob:uses-contract ref` dependents: symbols whose own
    contract depends on `ref`'s signature, so a change to `ref` invalidates
    THEIR correctness too, one hop out."""
    return {
        edge.src
        for edge in snapshot.edges
        if edge.target == ref and edge.kind == EdgeKind.USES_CONTRACT
    }


# frob:doc docs/modules/graph.md#affects
# frob:invariant INV-014
# frob:tests tests/test_graph_affects.py::TestAffects.test_direct_doc_and_test_edges
# frob:tests tests/test_graph_affects.py::TestAffects.test_transitive_uses_contract_chain  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestAffects.test_cycle_guarded
# frob:tests tests/test_graph_affects.py::TestAffects.test_truncated_at_max_depth
# frob:tests tests/test_graph_affects.py::TestAffects.test_truncated_at_max_nodes
# frob:tests tests/test_graph_affects.py::TestAffects.test_no_edges_is_empty_set
# frob:ticket T-0972
def affects(
    snapshot: GraphSnapshot,
    ref: str,
    *,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    max_nodes: int = _DEFAULT_MAX_NODES,
) -> AffectedSet:
    """Bounded BFS from `ref` over `uses-contract` reverse edges (a
    dependent's `frob:uses-contract ref` directive means the dependent's own
    correctness is a function of `ref`'s signature, so a change to `ref`
    propagates to it too) -- depth-limited, node-count-capped, cycle-guarded
    (a visited set), same shape as `frob.graph.callgraph.closure`. At every
    node visited (`ref` itself plus every dependent reached), the doc
    anchors (`frob:doc` + `frob:describes`) and tests (`frob:tests`)
    covering that node are folded into the returned `AffectedSet` -- so the
    result is not just "what depends on X" but "what documentation and what
    tests must be reviewed because X changed", exactly the north-star query
    (CLAUDE.md, T-0325). Pure: never mutates `snapshot`, never touches disk.
    """
    visited: set[str] = {ref}
    dependents: set[str] = set()
    docs: set[str] = set(_doc_targets_for(snapshot, ref))
    tests: set[str] = set(_test_refs_for(snapshot, ref))

    queue: deque[tuple[str, int]] = deque([(ref, 0)])
    truncated = False
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            if _dependents_of(snapshot, node) - visited:
                truncated = True
            continue
        for dep in sorted(_dependents_of(snapshot, node)):
            if dep in visited:
                continue
            if len(visited) >= max_nodes:
                truncated = True
                _log.warning("affects(%r): truncated at max_nodes=%d", ref, max_nodes)
                break
            visited.add(dep)
            dependents.add(dep)
            docs |= _doc_targets_for(snapshot, dep)
            tests |= _test_refs_for(snapshot, dep)
            queue.append((dep, depth + 1))
        if truncated:
            break

    _log.info(
        "affects(%r): %d dependent(s), %d doc(s), %d test(s), truncated=%s",
        ref,
        len(dependents),
        len(docs),
        len(tests),
        truncated,
    )
    return AffectedSet(
        root=ref,
        dependents=tuple(sorted(dependents)),
        docs=tuple(sorted(docs)),
        tests=tuple(sorted(tests)),
        truncated=truncated,
    )


# frob:doc docs/modules/graph.md#scope-closure-t-0998
class ScopeClosureGap(BaseModel):
    """One file a ticket's declared `scope` probably needs but does not
    have (T-0998): a `code_missing_doc` gap is a scoped code symbol whose
    `frob:doc`/`frob:describes` target file is NOT in scope; a
    `doc_missing_code` gap is the reverse -- a scoped doc anchor whose
    described code file is not in scope. Reuses the SAME `frob:doc`/
    `frob:describes` edges `_doc_targets_for` already reads for `affects()`
    -- this is scope-DECLARATION-time closure math over the identical
    edge set `affects()` walks at diff-time (AFFECT001/002), not a second
    traversal engine."""

    model_config = ConfigDict(frozen=True)

    direction: str
    scoped_site: str
    target: str
    missing_file: str


def _add_scope_gap(
    gaps: list[ScopeClosureGap],
    seen: set[tuple[str, str, str]],
    direction: str,
    site: str,
    target: str,
    missing_file: str,
) -> None:
    """Append one deduplicated `ScopeClosureGap` to `gaps` (extracted
    T-0861): the ONE dedup-by-`(direction, site, target)` shape
    `scope_doc_code_gaps` and `scope_test_gaps` each close over locally --
    a plain module-level function (not a closure) since both callers
    already hold their own `gaps`/`seen` accumulators explicitly."""
    key = (direction, site, target)
    if key in seen:
        return
    seen.add(key)
    gaps.append(
        ScopeClosureGap(
            direction=direction,
            scoped_site=site,
            target=target,
            missing_file=missing_file,
        )
    )


# frob:doc docs/modules/graph.md#scope-closure-t-0998
# frob:ticket T-0998
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_code_in_scope_doc_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_doc_in_scope_code_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_clean_when_both_sides_in_scope  # noqa: E501
def scope_doc_code_gaps(
    snapshot: GraphSnapshot, scope: tuple[str, ...] | list[str]
) -> tuple[ScopeClosureGap, ...]:
    """T-0998 direction (1)+(2): walk the `frob:doc`/`frob:describes` edges
    over every symbol/doc anchor already in `scope` and surface the exact
    file on the OTHER side of each edge that `scope` does not cover -- code
    in scope whose doc target is unscoped (direction 1), and docs in scope
    whose described code is unscoped (direction 2). Pure, snapshot-only (no
    disk IO, no git) -- `scope_matches` is imported lazily to avoid a
    module-load-order cycle with `frob.tickets` (this module is imported
    from `frob.graph.__init__` before that package finishes loading)."""
    from frob.tickets._models import scope_matches

    gaps: list[ScopeClosureGap] = []
    seen: set[tuple[str, str, str]] = set()

    scoped_symbols = sorted(
        ref for ref in snapshot.symbols if scope_matches(ref.split("::", 1)[0], scope)
    )
    for ref in scoped_symbols:
        for target in sorted(_doc_targets_for(snapshot, ref)):
            doc_file = target.split("#", 1)[0]
            if not scope_matches(doc_file, scope):
                _add_scope_gap(gaps, seen, "code_missing_doc", ref, target, doc_file)

    for edge in snapshot.edges:
        if edge.kind == EdgeKind.DOC:
            doc_file = edge.target.split("#", 1)[0]
            code_file = edge.src.split("::", 1)[0]
        elif edge.kind == EdgeKind.DESCRIBES:
            doc_file = edge.src.split("#", 1)[0]
            code_file = edge.target.split("::", 1)[0]
        else:
            continue
        if scope_matches(doc_file, scope) and not scope_matches(code_file, scope):
            doc_site = edge.target if edge.kind == EdgeKind.DOC else edge.src
            code_ref = edge.src if edge.kind == EdgeKind.DOC else edge.target
            _add_scope_gap(
                gaps, seen, "doc_missing_code", doc_site, code_ref, code_file
            )

    return tuple(gaps)


# frob:doc docs/modules/graph.md#scope-closure-t-0998
# frob:ticket T-0998
# frob:tests tests/test_graph_affects.py::TestScopeTestGaps.test_code_in_scope_test_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeTestGaps.test_test_in_scope_code_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeTestGaps.test_clean_when_both_sides_in_scope  # noqa: E501
def scope_test_gaps(
    snapshot: GraphSnapshot, scope: tuple[str, ...] | list[str]
) -> tuple[ScopeClosureGap, ...]:
    """T-0998 test-edge closure direction (symmetric with `scope_doc_code_
    gaps`'s doc-edge closure): a `frob:tests` edge is `src=test symref,
    target=code symref` (`_test_refs_for`'s own read direction). Scoped
    code implies its covering test FILE in scope (`code_missing_test`,
    mirrors `code_missing_doc` -- code edits with no covering test scoped
    is exactly the reactive-scope-add churn this ticket exists to close);
    scoped test files imply their covered code file in scope
    (`test_missing_code`, mirrors `doc_missing_code`). Reuses the SAME
    `EdgeKind.TESTS` edges `affects()`'s `_test_refs_for` already reads --
    no second traversal engine."""
    from frob.tickets._models import scope_matches

    gaps: list[ScopeClosureGap] = []
    seen: set[tuple[str, str, str]] = set()

    scoped_symbols = sorted(
        ref for ref in snapshot.symbols if scope_matches(ref.split("::", 1)[0], scope)
    )
    for ref in scoped_symbols:
        for test_ref in sorted(_test_refs_for(snapshot, ref)):
            test_file = test_ref.split("::", 1)[0]
            if not scope_matches(test_file, scope):
                _add_scope_gap(
                    gaps, seen, "code_missing_test", ref, test_ref, test_file
                )

    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        test_file = edge.src.split("::", 1)[0]
        code_file = edge.target.split("::", 1)[0]
        if scope_matches(test_file, scope) and not scope_matches(code_file, scope):
            _add_scope_gap(
                gaps, seen, "test_missing_code", edge.src, edge.target, code_file
            )

    return tuple(gaps)


__all__ = [
    "AffectedSet",
    "ScopeClosureGap",
    "affects",
    "scope_doc_code_gaps",
    "scope_test_gaps",
]
