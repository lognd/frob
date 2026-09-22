"""INV007/INV008: the two `frob:invariant` obligation forms T-0757 adds
(docs/modules/gates.md#inv007-and-inv008-t-0757), turning the T-0611/T-0682
design-invariant bug class into gates instead of prose only a human
reviewer remembers.

T-0611's actual incident: `src/frob/arch/_normalized.py` is a deliberately
tree_sitter-free pure model module (every adapter -- `_python.py`,
`_typescript.py`, ... -- lives outside it precisely so this module never
needs a parser import); a reviewer caught a `TypeScriptAdapter` landing
INSIDE `_normalized.py` by reading the diff, not by any check. INV007
makes that class of design invariant ("module M must never import
package P") a static, code-anchored obligation: `frob:invariant INV-###
no_import="tree_sitter"` on a module declares it, and INV007 fails the
instant the file's own raw import specifiers (`frob.lang.extract_imports`
-- the same primitive `frob.arch._smells`/`frob.arch._layering` already
use for project-wide import graphs, T-0625/T-0620) contain a prefix match
against any declared forbidden module.

T-0682's incident is the other shape: `frob.tickets._land.splice_ledger`'s
`_newer` comparator carries a subtle ORDERING PROPERTY (a Done-report side
only wins over a reportless side when the reportless side does not
strictly outrank it) that a first-pass fix got wrong in the OPPOSITE
direction from the bug it was fixing, twice, because the property lived
only in a reviewer's head. INV008 makes "this property must be
established, and stay established, by a real property-style regression
test" checkable: `frob:invariant INV-### establishes="..."` on the
comparator requires a `frob:tests ... kind="property"` edge (T-0757 widens
`frob.graph.dsl._TESTS_KINDS`) bound to that same anchor -- a bare example
test does not satisfy it, matching INV005's existing "evidence must
actually reach the anchor" doctrine one step further: the reaching
evidence must ALSO be declared as exercising the property space, not one
fixed input.

Both obligation forms parse through the SAME `frob:invariant` directive
(`frob.graph.dsl`'s `no_import=`/`establishes=` attrs) rather than new
verbs -- an invariant can still be a bare `frob:invariant INV-###` anchor
with neither attribute, unaffected by this module.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.lang import extract_imports
from frob.logging import get_logger

_log = get_logger(__name__)

# T-3962: the naming convention a `frob:invariant ... guards="..."`
# obligation's frozenset must match -- FORBIDDEN/EXCLUDED/ALLOWED as
# either a prefix (F-175's own `EXCLUDED_TABLES`/`FORBIDDEN_COLUMNS`) or
# a suffix component (`_`-delimited on both sides), so INV011 only fires
# for a constant this pattern recognizes as a guard (a misnamed constant
# is simply not INV011's business; see `inv011_violations`'s docstring
# for the F-175 incident this generalizes).
_GUARD_NAME_RE = re.compile(r"(^|_)(FORBIDDEN|EXCLUDED|ALLOWED)(_|$)")


def _anchor_file(edge: Edge) -> str:
    """The repo-relative file path a `frob:invariant` edge's `src` binds
    to, stripping any trailing `::qualname` symbol suffix (an anchor can
    bind to a whole file or to one symbol inside it; INV007's import scan
    is always file-level, so only the file half matters)."""
    return edge.src.split("::", 1)[0]


def _forbidden_modules(edge: Edge) -> tuple[str, ...]:
    """The comma-separated `no_import="pkg[,pkg2,...]"` list on `edge`, or
    `()` if this invariant edge declares no import-forbidding obligation."""
    raw = edge.attrs.get("no_import")
    if not raw:
        return ()
    return tuple(m.strip() for m in raw.split(",") if m.strip())


def _import_violates(spec: str, forbidden: str) -> bool:
    """Whether a raw import specifier `spec` (as `frob.lang.extract_imports`
    returns it, e.g. `"tree_sitter"` or `"tree_sitter.language"`) imports
    `forbidden` itself or any of its submodules -- a prefix match on `.`
    boundaries, not a bare substring match (`tree_sitter_python` must NOT
    trip a `no_import="tree_sitter"` obligation)."""
    return spec == forbidden or spec.startswith(f"{forbidden}.")


# frob:doc docs/modules/gates.md#inv007-and-inv008-t-0757
# frob:ticket T-0757
# frob:enforces CHK-GATE-INV007
def inv007_violations(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """INV007: a `frob:invariant ... no_import="pkg"` anchor whose own file
    actually imports (a raw specifier match, not a resolved/transitive
    one -- direct imports are exactly what T-0611's incident was) a
    forbidden module or one of its submodules. ERROR severity: unlike
    INV003/INV004/INV006's advisory doc-prose scans, this fires only for
    an EXPLICITLY declared obligation (never a bare-vocabulary heuristic),
    so there is no first-turn-on debt corpus to phase in against."""
    violations: list[Violation] = []
    seen: set[tuple[str, str]] = set()
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.INVARIANT:
            continue
        forbidden = _forbidden_modules(edge)
        if not forbidden:
            continue
        rel = _anchor_file(edge)
        path = root / rel
        result = extract_imports(path)
        if result.is_err:
            _log.debug(
                "INV007: %s: could not extract imports (%s)", rel, result.danger_err
            )
            continue
        specs = result.danger_ok
        for module in forbidden:
            key = (rel, module)
            if key in seen:
                continue
            hits = tuple(s for s in specs if _import_violates(s, module))
            if not hits:
                continue
            seen.add(key)
            # frob:waive PERF004 reason="hits is this (file, module) pair's own tiny \
            # distinct import-specifier set (a handful of matches within one file at \
            # most, bounded by how many raw import statements the file itself has) -- \
            # not a shared collection re-sorted identically across outer-loop \
            # iterations"
            hits_sorted = ", ".join(sorted(set(hits)))
            _log.warning(
                "INV007: %s imports forbidden module %r (%s), violating %s",
                rel,
                module,
                hits_sorted,
                edge.target,
            )
            violations.append(
                Violation(
                    rule="INV007",
                    severity=Severity.ERROR,
                    file=rel,
                    line=0,
                    message=(
                        f"INV007: {rel} imports forbidden module {module!r} "
                        f"({hits_sorted}), violating "
                        f"{edge.target}'s frob:invariant no_import={module!r} "
                        f"obligation"
                    ),
                )
            )
    return tuple(violations)


def _establishes_claims(snapshot: GraphSnapshot) -> tuple[Edge, ...]:
    """Every `frob:invariant ... establishes="..."` edge in `snapshot` --
    an `EdgeKind.INVARIANT` filter (shared via `_edges_of_kind`, T-1114)
    narrowed further to only the subset that also carries an
    `establishes=` attribute, distinct from `_debt_edges`/
    `_deprecated_edges`/`_waive_edges`'s pure kind-only filters."""
    from frob.gates import _edges_of_kind

    return tuple(
        e
        for e in _edges_of_kind(snapshot, EdgeKind.INVARIANT)
        if e.attrs.get("establishes")
    )


def _has_bound_property_test(anchor_src: str, snapshot: GraphSnapshot) -> bool:
    """Whether some `frob:tests ... kind="property"` edge reaches
    `anchor_src` from either direction, mirroring `frob.gates.
    _evidence_binds_to_symrefs`'s either-side TESTS-edge walk: the usual
    convention binds the directive to the CODE symbol (`src=anchor`,
    `target=test node id`), but a directive placed on the test itself
    pointing back at the code (`src=test`, `target=anchor`) is accepted
    too, same as INV005's own evidence-reaches-anchor check."""
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS or edge.attrs.get("kind") != "property":
            continue
        if anchor_src in (edge.src, edge.target):
            return True
    return False


# frob:doc docs/modules/gates.md#inv007-and-inv008-t-0757
# frob:ticket T-0757
# frob:enforces CHK-GATE-INV008
def inv008_violations(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """INV008: a `frob:invariant ... establishes="..."` anchor with no
    `frob:tests ... kind="property"` edge reaching it -- an establish-
    property obligation demands a test declared as exercising the
    property SPACE (a comparator's ordering, a round-trip, a monotonicity
    claim), not merely one fixed-input example. ERROR severity, same
    posture as INV007: an explicitly-declared obligation with no debt
    corpus to phase in against."""
    violations: list[Violation] = []
    for edge in _establishes_claims(snapshot):
        if _has_bound_property_test(edge.src, snapshot):
            continue
        file, _, line = edge.origin.rpartition(":")
        _log.warning(
            'INV008: %s establishes=%r has no bound kind="property" test',
            edge.target,
            edge.attrs.get("establishes"),
        )
        violations.append(
            Violation(
                rule="INV008",
                severity=Severity.ERROR,
                file=file or edge.origin,
                line=int(line) if line.isdigit() else 0,
                message=(
                    f"INV008: {edge.target}'s establish-property obligation "
                    f"({edge.attrs.get('establishes')!r}) has no "
                    f'frob:tests ... kind="property" edge bound to '
                    f"{edge.src}; add one that actually exercises the "
                    f"declared property, not a single fixed-input example"
                ),
            )
        )
    return tuple(violations)


def _guard_name(edge: Edge) -> str | None:
    """The `guards="..."` frozenset name on `edge`, or `None` when absent
    or when it does not match `_GUARD_NAME_RE` (INV011 only recognizes a
    `*_FORBIDDEN`/`*_EXCLUDED`/`*_ALLOWED`-named guard, matching the
    F-175 incident's own vocabulary -- a differently-named constant is
    simply out of this obligation form's declared scope, not a malformed
    directive; `frob.graph.dsl` is not in this ticket's scope to add a
    stricter parse-time check)."""
    raw = edge.attrs.get("guards")
    if not raw or not _GUARD_NAME_RE.search(raw):
        return None
    return raw


def _entrypoints(edge: Edge) -> tuple[str, ...]:
    """The comma-separated `entrypoints="path::qual,path::qual2"` list on
    a `guards=` invariant edge -- the declared call-graph roots INV011
    walks from toward the guarded sink (`edge.src`)."""
    raw = edge.attrs.get("entrypoints")
    if not raw:
        return ()
    return tuple(e.strip() for e in raw.split(",") if e.strip())


def _guard_reaching_files(sink: str, entrypoints: tuple[str, ...]) -> tuple[str, ...]:
    """The distinct repo-relative files `sink` and `entrypoints` live in,
    sorted -- the `paths` INV011 scopes its own `build_call_graph` call
    to, mirroring `_cov006_third_file_reachable`'s pattern of scoping the
    shared call-graph builder to just the files one obligation check
    actually needs rather than the whole repo."""
    files = {_anchor_file_from_symref(sink)}
    files.update(_anchor_file_from_symref(e) for e in entrypoints)
    return tuple(sorted(files))


def _anchor_file_from_symref(symref: str) -> str:
    """The file half of a `path::qualname` symref -- shared by
    `_guard_reaching_files`'s sink/entrypoint file collection."""
    return symref.split("::", 1)[0]


# frob:ticket T-3962
def _guarded_nodes(
    root: Path, sink: str, graph, guard: str, references_name
) -> frozenset[str]:  # noqa: ANN001
    """Every node in `graph` (besides `sink` itself) that references
    `guard` -- the set INV011 excludes `closure` from expanding through,
    since a path passing through one of these has already consulted the
    guard."""
    return frozenset(
        node
        for node in {
            sink,
            *graph.calls.keys(),
            *(c for cs in graph.calls.values() for c in cs),
        }
        if node != sink and references_name(root, node, guard)
    )


def _inv011_entrypoint_violation(
    *,
    root: Path,
    edge: Edge,
    sink: str,
    ep: str,
    guard: str,
    graph,  # noqa: ANN001
    guarded_nodes: frozenset[str],
    references_name,  # noqa: ANN001
    closure,  # noqa: ANN001
) -> Violation | None:
    """One entrypoint's own check against a `guards=`/`entrypoints=`
    obligation: `None` when `ep`'s own path to `sink` is guarded (either
    `ep` itself references `guard`, or every call-graph path from `ep`
    to `sink` passes through a guard-referencing node), else the ERROR
    `Violation` naming the unguarded path."""
    if ep == sink or references_name(root, ep, guard):
        return None
    reachable = closure(graph, ep, exclude=guarded_nodes)
    if sink not in reachable:
        return None
    _log.warning(
        "INV011: %s reaches guarded sink %s without ever referencing %s",
        ep,
        sink,
        guard,
    )
    return Violation(
        rule="INV011",
        severity=Severity.ERROR,
        file=_anchor_file_from_symref(ep),
        line=0,
        message=(
            f"INV011: {ep} reaches guarded sink {sink} via a "
            f"call-graph path that never references the "
            f"{guard!r} frozenset, violating {edge.target}'s "
            f"frob:invariant guards={guard!r} obligation"
        ),
    )


def _inv011_edge_violations(root: Path, edge: Edge) -> tuple[Violation, ...]:
    """One `frob:invariant ... guards=/entrypoints=` obligation edge's own
    findings -- the per-edge substrate build (call graph scoped to
    `sink`/`entrypoints`' own files, guarded-node set) plus the
    per-entrypoint walk `_inv011_entrypoint_violation` does, split out of
    `inv011_violations` purely to keep that function's own body a plain
    edge-filtering loop."""
    from frob.graph.callgraph import build_call_graph, closure, references_name

    guard = _guard_name(edge)
    if guard is None:
        return ()
    sink = edge.src
    entrypoints = _entrypoints(edge)
    if not entrypoints:
        return ()
    if references_name(root, sink, guard):
        # The sink guards itself at the point of use -- every path
        # reaching it is inherently guarded; nothing to walk.
        return ()
    files = _guard_reaching_files(sink, entrypoints)
    graph = build_call_graph(root, files)
    guarded_nodes = _guarded_nodes(root, sink, graph, guard, references_name)
    violations: list[Violation] = []
    for ep in entrypoints:
        violation = _inv011_entrypoint_violation(
            root=root,
            edge=edge,
            sink=sink,
            ep=ep,
            guard=guard,
            graph=graph,
            guarded_nodes=guarded_nodes,
            references_name=references_name,
            closure=closure,
        )
        if violation is not None:
            violations.append(violation)
    return tuple(violations)


# frob:doc docs/modules/gate-inv011-forbidden-constant-reachability.md#inv011-forbidden-constant-reachability-t-3962  # noqa: E501
# frob:ticket T-3962
# frob:enforces CHK-GATE-INV011
def inv011_violations(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """INV011: forbidden-constant reachability (F-175, T-3962).

    A `frob:invariant INV-### guards="*_FORBIDDEN/*_EXCLUDED/*_ALLOWED"
    entrypoints="path::qual[,path::qual2,...]"` anchor (`edge.src` is the
    guarded SINK symref) declares that every call-graph path from each
    declared entrypoint to the sink must pass through at least one node
    that references the named frozenset. INV011 fires once per
    entrypoint whose path to the sink can dodge the guard entirely --
    naming that unguarded path -- reusing `frob.graph.callgraph`'s
    existing BFS substrate (`build_call_graph` + `closure`'s `exclude`
    param, T-3962) rather than a second call-graph traversal engine, same
    posture as `_cov006_third_file_reachable`. F-175's own incident this
    generalizes: `EXCLUDED_TABLES`/`FORBIDDEN_COLUMNS` was checked on
    three write paths and skipped on the fourth (`revert_change`) -- a
    reviewer-memory-only bug class this makes a static ERROR finding.
    Per-edge/per-entrypoint work lives in `_inv011_edge_violations`/
    `_inv011_entrypoint_violation`; this is a plain edge-filtering loop.
    """
    violations: list[Violation] = []
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.INVARIANT:
            violations.extend(_inv011_edge_violations(root, edge))
    return tuple(violations)


__all__ = ["inv007_violations", "inv008_violations", "inv011_violations"]
