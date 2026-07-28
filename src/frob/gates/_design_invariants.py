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
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's incident-by-incident mandate \
# summary), verifiable by reading the functions it annotates, not a separate \
# cross-module contract needing its own tracked invariant -- the same INV006 \
# first-turn-on-pool disposition frob.gates._ffi_boundary's own module docstring \
# already carries"

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.lang import extract_imports
from frob.logging import get_logger

_log = get_logger(__name__)


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
# frob:tests tests/unit/test_design_invariants.py::TestInv007.test_forbidden_import_fires  # noqa: E501
# frob:tests tests/unit/test_design_invariants.py::TestInv007.test_clean_module_no_finding  # noqa: E501
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
    """Every `frob:invariant ... establishes="..."` edge in `snapshot`."""
    return tuple(
        e
        for e in snapshot.edges
        if e.kind == EdgeKind.INVARIANT and e.attrs.get("establishes")
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
# frob:tests tests/unit/test_design_invariants.py::TestInv008.test_missing_property_test_fires  # noqa: E501
# frob:tests tests/unit/test_design_invariants.py::TestInv008.test_bound_property_test_clears  # noqa: E501
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


__all__ = ["inv007_violations", "inv008_violations"]
