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
        # frob:waive PERF004 reason="_dependents_of(snapshot, node) is this loop's own per-node distinct set, not a shared re-sort"  # noqa: E501
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


__all__ = ["AffectedSet", "affects"]
