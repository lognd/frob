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
from collections.abc import Iterable, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.graph._models import EdgeKind, GraphSnapshot
from frob.graph.callgraph import CallGraph
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


# frob:doc docs/modules/graph.md#caller-dependents-t-4553
# frob:ticket T-4553
# frob:tests tests/unit/test_check_scoped_files.py::TestCallerDependentFiles.test_direct_caller_files_found  # noqa: E501
# frob:tests tests/unit/test_check_scoped_files.py::TestCallerDependentFiles.test_already_covered_files_excluded  # noqa: E501
# frob:tests tests/unit/test_check_scoped_files.py::TestCallerDependentFiles.test_capped_at_max_added  # noqa: E501
def caller_dependent_files(
    graph: CallGraph,
    changed_symrefs: Iterable[str],
    already_covered: frozenset[str],
    *,
    max_added: int = 200,
) -> tuple[frozenset[str], bool]:
    """One hop of CALLER files for every symref in `changed_symrefs`, read
    off an already-built `frob.graph.callgraph.CallGraph` (T-4553): for
    every `caller -> callees` edge where one of `callees` is a changed
    symref, the caller's own file is a direct dependent -- `affects()`
    above only follows `frob:uses-contract` directive edges, so a plain
    (undirectived) caller of a changed symbol was previously invisible to
    the rapid land scope check T-4413 introduced.

    Pure -- no disk IO, no graph building: `graph` must already be built
    by the caller, and `build_call_graph(..., verify_imports=True)` is the
    intended source (see `frob.vet._capability_python`'s own T-2188
    lesson: an unrestricted, bare-short-name match cross-wires same-named
    helpers living in unrelated files repo-wide, so `verify_imports=True`
    -- which resolves a cross-file candidate only when the caller's file
    actually imports the callee's file -- is load-bearing here, not
    optional).

    Files already in `already_covered` (the touched set, or anything the
    `uses-contract` walk already added) are never re-added. Capped at
    `max_added` newly-added files -- `truncated=True` in the returned
    `(files, truncated)` pair means the cap cut the result short and the
    caller should log a WARN naming the cap, matching `affects()`'s own
    `max_nodes` truncation contract above."""
    changed = frozenset(changed_symrefs)
    added: set[str] = set()
    for caller, callees in graph.calls.items():
        caller_file = caller.split("::", 1)[0]
        if caller_file in already_covered:
            continue
        if changed.isdisjoint(callees):
            continue
        added.add(caller_file)
    truncated = len(added) > max_added
    if truncated:
        added = set(sorted(added)[:max_added])
    return frozenset(added), truncated


# frob:doc docs/modules/graph.md#caller-dependents-t-4553
# frob:ticket T-4560
# frob:tests \
# tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles.test_public_callee_caller_is_found_through_import_binding  # noqa: E501
# frob:tests \
# tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles.test_same_named_private_helpers_in_different_modules_stay_unlinked  # noqa: E501
def public_caller_dependent_files(
    root: Path,
    all_paths: Sequence[str],
    changed_symrefs: Iterable[str],
    already_covered: frozenset[str],
    *,
    max_added: int = 200,
) -> tuple[frozenset[str], bool]:
    """`caller_dependent_files`'s public-symbol-aware sibling (T-4560):
    `build_call_graph`'s existing private-only `CallGraph.calls` (the
    shared graph `frob.dup`/`frob.gates` also consume, see that
    function's own docstring for why it is never narrowed for one
    consumer) misses every caller of a changed PUBLIC symbol -- disclosed
    by the T-4553 implementer, since `caller_dependent_files` alone
    cannot see an edge that was never recorded. This builds a SEPARATE,
    opt-in `CallGraph` via `build_call_graph(root, all_paths, verify_
    imports=True, include_public_callees=True)` (import-binding-verified,
    never a bare repo-wide short-name match -- the T-2188 hazard
    `include_public_callees` itself guards against) and reuses `caller_
    dependent_files`'s own resolution loop over it unchanged.

    Deliberately a SECOND graph, not a mutation of a caller-supplied one:
    the existing `caller_dependent_files(graph, ...)` contract keeps
    working against a private-only graph exactly as before for any
    other consumer that has not opted in.

    Parameters mirror `frob.graph.callgraph.build_call_graph`'s own
    (`root`, `all_paths`) plus `caller_dependent_files`'s own
    (`changed_symrefs`, `already_covered`, `max_added`) -- the intended
    caller is `frob.app.ticket_runner._land_cmd._rapid_caller_
    dependents`, which builds its `all_paths`/`changed`/`already` inputs
    identically for both this and the private-only call today."""
    from frob.graph.callgraph import build_call_graph

    public_graph = build_call_graph(
        root, all_paths, verify_imports=True, include_public_callees=True
    )
    return caller_dependent_files(
        public_graph, changed_symrefs, already_covered, max_added=max_added
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


# frob:ticket T-3412
def _ref_file(ref: str) -> str:
    """The bare file path underneath a symref/anchor `ref` (T-3412): strips
    a code symref's `::qualname` suffix AND a doc anchor's `#anchor`
    suffix, whichever is present -- so a scope glob covering the whole
    file (`'docs/x.md'`) matches consistently regardless of whether `ref`
    names a code symbol (`'a.py::foo'`), a doc anchor
    (`'docs/x.md#foo'`), or a code-side ref that happens to itself be
    ANOTHER doc anchor (a `DESCRIBES`/`DOC` edge between two anchors in
    the same guide, common in self-referencing docs). Before this, only
    `::` or only `#` was stripped depending on which side of the edge
    `ref` came from, so an anchor-shaped ref reaching the `::`-only split
    (or vice versa) kept its suffix and never matched a whole-file scope
    entry -- the root cause of T-3412's "adding a doc FILE to scope does
    not subsume its own anchors" (272 closure warnings on one `--add`)."""
    return ref.split("::", 1)[0].split("#", 1)[0]


# frob:doc docs/modules/graph.md#scope-closure-t-0998
# frob:ticket T-0998
# frob:ticket T-3412
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_code_in_scope_doc_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_doc_in_scope_code_target_unscoped  # noqa: E501
# frob:tests tests/test_graph_affects.py::TestScopeDocCodeGaps.test_clean_when_both_sides_in_scope  # noqa: E501
# frob:tests \
# tests/test_graph_affects.py::TestScopeDocCodeGaps.test_scoping_the_whole_doc_file_subsumes_its_own_anchors  # noqa: E501
# frob:tests \
# tests/test_graph_affects.py::TestScopeDocCodeGaps.test_scoping_the_whole_doc_file_still_flags_a_genuinely_unscoped_anchor  # noqa: E501
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
        ref for ref in snapshot.symbols if scope_matches(_ref_file(ref), scope)
    )
    for ref in scoped_symbols:
        for target in sorted(_doc_targets_for(snapshot, ref)):
            doc_file = _ref_file(target)
            if not scope_matches(doc_file, scope):
                _add_scope_gap(gaps, seen, "code_missing_doc", ref, target, doc_file)

    for edge in snapshot.edges:
        if edge.kind == EdgeKind.DOC:
            doc_file = _ref_file(edge.target)
            code_file = _ref_file(edge.src)
        elif edge.kind == EdgeKind.DESCRIBES:
            doc_file = _ref_file(edge.src)
            code_file = _ref_file(edge.target)
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
    "caller_dependent_files",
    "public_caller_dependent_files",
    "scope_doc_code_gaps",
    "scope_test_gaps",
]
