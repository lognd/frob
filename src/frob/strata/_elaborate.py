"""std.trust elaborator: surface AST -> kernel facts (docs/strata/surface.md).

A vocabulary is a pure function `surface construct -> kernel facts` (charter
law 1, docs/strata/surface.md#elaborator). `std.trust` is the only
vocabulary this module knows: nodes, flows, endorse/declassify boundaries,
and noflow/reach/bound claims. Elaboration never re-validates what the Rust
parser already guarantees (grammar shape, closed keyword vocabulary); it
only adds the checks the parser cannot make because they span multiple
declarations -- duplicate ids and dangling references.
"""

from __future__ import annotations

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import BoundaryDecl, ClaimDecl, FlowDecl, Module, NodeDecl
from ._errors import StrataError
from ._models import (
    Boundary,
    BoundaryDirection,
    BoundClaim,
    Capacity,
    Claim,
    ClaimBody,
    Flow,
    KernelModel,
    Metric,
    Node,
    NoFlow,
    Reach,
)

_log = get_logger(__name__)

#: Node attr marker for `is_abstract` nodes; refinement proper is T-0062.
_ABSTRACT_ATTR = "abstract"


def _elaborate_node(decl: NodeDecl) -> Node:
    """One `NodeDecl` -> one kernel `Node`; abstract nodes gain an attrs marker."""
    attrs = decl.attrs
    if decl.is_abstract:
        _log.debug(
            "node %s is abstract; marking attrs with %r", decl.id, _ABSTRACT_ATTR
        )
        attrs = (*attrs, _ABSTRACT_ATTR)
    capacity = None
    if decl.capacity is not None:
        capacity = Capacity(
            service_rate=decl.capacity.rate,
            replicas_min=decl.capacity.replicas_min,
            replicas_max=decl.capacity.replicas_max,
        )
    return Node(
        id=decl.id,
        trust=decl.trust,
        clearance=decl.clearance,
        attrs=attrs,
        capacity=capacity,
        residence=decl.residence,
    )


def _elaborate_flow(decl: FlowDecl) -> Flow:
    """One `FlowDecl` -> one kernel `Flow`; a direct field-for-field mapping."""
    return Flow(
        id=decl.id,
        src=decl.src,
        dst=decl.dst,
        label=decl.label,
        rate=decl.rate,
        age=decl.age,
        size=decl.size,
        transport=decl.transport,
        attrs=decl.attrs,
    )


def _elaborate_boundary(decl: BoundaryDecl) -> Boundary:
    """One `BoundaryDecl` -> one `Boundary`; `kind` maps to `BoundaryDirection`."""
    return Boundary(
        id=decl.id,
        flow_id=decl.flow_id,
        direction=BoundaryDirection(decl.kind),
        from_level=decl.from_level,
        to_level=decl.to_level,
        predicate=decl.predicate,
    )


def _elaborate_claim_body(decl: ClaimDecl) -> ClaimBody:
    """The claim `kind` selects which kernel claim body shape to build.

    The parser's `kind` vocabulary is closed to "noflow"/"reach"/"bound"
    (docs/strata/surface.md grammar); anything else cannot reach this
    function post-parse, so there is no defensive fallback branch here.
    The `assert`s below only narrow the type checker's view of the AST's
    per-kind-optional fields, which the parser has already guaranteed are
    populated for the matching `kind` -- they are not runtime validation.
    """
    if decl.kind == "noflow":
        assert decl.src is not None and decl.dst is not None
        return NoFlow(src=decl.src, dst=decl.dst)
    if decl.kind == "reach":
        assert decl.src is not None and decl.dst is not None
        return Reach(src=decl.src, dst=decl.dst)
    assert (
        decl.metric is not None and decl.target is not None and decl.limit is not None
    )
    return BoundClaim(metric=Metric(decl.metric), target=decl.target, limit=decl.limit)


def _elaborate_claim(decl: ClaimDecl) -> Claim:
    """One `ClaimDecl` -> one kernel `Claim`; assumed/owner/review pass through."""
    return Claim(
        id=decl.id,
        body=_elaborate_claim_body(decl),
        assumed=decl.assumed,
        owner=decl.owner,
        review=decl.review,
    )


def _validate_no_duplicates(module: Module) -> Result[None, StrataError]:
    """Node ids and flow ids must each be unique within their own kind.

    This is elaboration-level, not parser-level: the grammar has no notion
    of "already declared", so two nodes sharing an id parse cleanly and
    only become a fault once the elaborator tries to build one kernel
    model out of them.
    """
    for kind, ids in (
        ("node", [n.id for n in module.nodes]),
        ("flow", [f.id for f in module.flows]),
    ):
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            _log.error("duplicate %s id(s) in module %s: %s", kind, module.name, dupes)
            return Err(StrataError.DuplicateId)
    return Ok(None)


def _validate_references(module: Module) -> Result[None, StrataError]:
    """Boundary flow references and bound-claim targets must resolve.

    `noflow`/`reach` src/dst are left alone here -- they name either a
    node id or a trust level, and only the kernel's `FactBase` knows the
    model's trust lattice well enough to expand a level into its nodes
    (docs/strata/kernel.md#fact-base), so checking them prematurely would
    duplicate that logic and risk disagreeing with it.
    """
    known_nodes = {n.id for n in module.nodes}
    known_flows = {f.id for f in module.flows}
    for boundary in module.boundaries:
        if boundary.flow_id not in known_flows:
            _log.error(
                "boundary %s references unknown flow %r", boundary.id, boundary.flow_id
            )
            return Err(StrataError.UnknownReference)
    for claim in module.claims:
        if claim.kind == "bound" and claim.target not in (known_nodes | known_flows):
            _log.error("claim %s references unknown target %r", claim.id, claim.target)
            return Err(StrataError.UnknownReference)
    return Ok(None)


# frob:doc docs/strata/surface.md#elaborator
def elaborate(module: Module) -> Result[KernelModel, StrataError]:
    """Elaborate a parsed `Module` into a `KernelModel` under `std.trust`.

    WHY: this is the only place that knows what a surface `node`, `flow`,
    `boundary`, or `assert`/`assume` means (charter law 1); the prover
    downstream never sees a vocabulary word. Fails closed, logging at
    ERROR, on cross-declaration faults the Rust parser cannot see:
    duplicate node/flow ids, a boundary naming an unknown flow, or a
    bound claim naming an unknown target.
    """
    dupes_ok = _validate_no_duplicates(module)
    if dupes_ok.is_err:
        return Err(dupes_ok.danger_err)
    refs_ok = _validate_references(module)
    if refs_ok.is_err:
        return Err(refs_ok.danger_err)

    model = KernelModel(
        nodes=tuple(_elaborate_node(n) for n in module.nodes),
        flows=tuple(_elaborate_flow(f) for f in module.flows),
        boundaries=tuple(_elaborate_boundary(b) for b in module.boundaries),
        claims=tuple(_elaborate_claim(c) for c in module.claims),
    )
    _log.info(
        "elaborated module %s: %d node(s), %d flow(s), %d boundary(ies), %d claim(s)",
        module.name,
        len(model.nodes),
        len(model.flows),
        len(model.boundaries),
        len(model.claims),
    )
    return Ok(model)
