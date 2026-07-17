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

from ._ast import BoundaryDecl, ClaimDecl, FlowDecl, Module, NodeDecl, RefineDecl
from ._errors import StrataError
from ._infra import elaborate_infra
from ._models import (
    TRUST,
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
    duplicate that logic and risk disagreeing with it. Bound-claim targets
    may also name a std.infra node (store/cache/queue/cdn/balancer) --
    those ids are known even though `elaborate_infra` has not run yet,
    since the id itself is a parser-guaranteed field on each infra decl
    (docs/strata/surface.md#std-infra), not something only desugaring
    computes.
    """
    known_nodes = {n.id for n in module.nodes}
    known_nodes |= {s.id for s in module.stores}
    known_nodes |= {c.id for c in module.caches}
    known_nodes |= {q.id for q in module.queues}
    known_nodes |= {c.id for c in module.cdns}
    known_nodes |= {b.id for b in module.balancers}
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


def _rewire_endpoint(value: str, target: str, bind_to: str) -> str:
    """Replace `value` with `bind_to` when it names the refine target."""
    return bind_to if value == target else value


def _rewrite_claim_for_refine(claim: Claim, refine: RefineDecl) -> Claim:
    """Rewrite one claim's endpoints/target from a refine's abstraction id to `bind_to`.

    Flattening a refine block must not leave a claim dangling on an id that
    no longer exists in the model (the abstract node was just removed), so
    every claim naming the target is re-pointed at `bind_to` -- logged at
    INFO since this changes what the claim literally asserts, even though
    its truth is preserved by the faithfulness checks.
    """
    body = claim.body
    if isinstance(body, NoFlow | Reach):
        if body.src == refine.target or body.dst == refine.target:
            new_body = type(body)(
                src=_rewire_endpoint(body.src, refine.target, refine.bind_to),
                dst=_rewire_endpoint(body.dst, refine.target, refine.bind_to),
            )
            _log.info(
                "refine %s: rewriting claim %s endpoint(s) %s -> %s to bind_to %s",
                refine.target,
                claim.id,
                body.src,
                body.dst,
                refine.bind_to,
            )
            return claim.model_copy(update={"body": new_body})
    elif isinstance(body, BoundClaim) and body.target == refine.target:
        _log.info(
            "refine %s: rewriting claim %s target to bind_to %s",
            refine.target,
            claim.id,
            refine.bind_to,
        )
        return claim.model_copy(
            update={"body": body.model_copy(update={"target": refine.bind_to})}
        )
    return claim


def _apply_refine(
    refine: RefineDecl,
    nodes: dict[str, Node],
    flows: list[Flow],
    claims: list[Claim],
) -> Result[None, StrataError]:
    """Flatten one `refine` block into `nodes`/`flows`/`claims` in place.

    WHY: this is the compositional-proof mechanism (docs/strata/surface.md
    #refinement) -- an abstract node is swapped for its concrete internals
    only once two of the three faithfulness checks pass (no new external
    surface, no trust laundering); the third, budget distribution, is
    DEFERRED to phase 2 and intentionally not checked here. Every outer
    flow and claim endpoint naming the abstraction is rewired to `bind_to`
    so the flattened model has no dangling reference to the removed id.
    """
    target = nodes.get(refine.target)
    if target is None:
        _log.error("refine target %r is not declared in the module", refine.target)
        return Err(StrataError.RefinementViolation)
    if _ABSTRACT_ATTR not in target.attrs:
        _log.error("refine target %r is not declared abstract", refine.target)
        return Err(StrataError.RefinementViolation)

    inner_nodes = [_elaborate_node(n) for n in refine.nodes]
    inner_flows = [_elaborate_flow(f) for f in refine.flows]
    inner_ids = {n.id for n in inner_nodes}

    # Faithfulness check 1: no new external surface -- every inner flow's
    # endpoints must both stay inside the refined assembly.
    for flow in inner_flows:
        if flow.src not in inner_ids or flow.dst not in inner_ids:
            _log.error(
                "refine %r: inner flow %r (%s -> %s) touches an id outside the "
                "refined assembly (new external surface)",
                refine.target,
                flow.id,
                flow.src,
                flow.dst,
            )
            return Err(StrataError.RefinementViolation)

    # Faithfulness check 2: no trust laundering -- every inner node must sit
    # at or above the abstraction's declared trust in the trust lattice.
    for inner in inner_nodes:
        leq = TRUST.leq(target.trust, inner.trust)
        if leq.is_err:
            return Err(leq.danger_err)
        if not leq.danger_ok:
            _log.error(
                "refine %r: inner node %r trust %r is below abstraction trust "
                "%r (trust laundering)",
                refine.target,
                inner.id,
                inner.trust,
                target.trust,
            )
            return Err(StrataError.RefinementViolation)

    # Faithfulness check 3, budget distribution (parent bounds must cover
    # the concrete paths), is DEFERRED to phase 2 -- see
    # docs/strata/surface.md#v0-semantics. No check is performed here.

    if refine.bind_to not in inner_ids:
        _log.error(
            "refine %r: bind_to %r is not one of the inner node ids %s",
            refine.target,
            refine.bind_to,
            sorted(inner_ids),
        )
        return Err(StrataError.RefinementViolation)

    del nodes[refine.target]
    for inner in inner_nodes:
        nodes[inner.id] = inner
    flows.extend(inner_flows)

    for i, flow in enumerate(flows):
        if flow.src == refine.target or flow.dst == refine.target:
            new_src = _rewire_endpoint(flow.src, refine.target, refine.bind_to)
            new_dst = _rewire_endpoint(flow.dst, refine.target, refine.bind_to)
            _log.info(
                "refine %s: rewiring flow %s %s -> %s to bind_to %s",
                refine.target,
                flow.id,
                flow.src,
                flow.dst,
                refine.bind_to,
            )
            flows[i] = flow.model_copy(update={"src": new_src, "dst": new_dst})

    for i, claim in enumerate(claims):
        claims[i] = _rewrite_claim_for_refine(claim, refine)

    return Ok(None)


def _elaborate_refines(
    module: Module, model: KernelModel
) -> Result[KernelModel, StrataError]:
    """Flatten every `refine` block in `module` into `model`.

    WHY: refinement happens after the base model exists so a refine block
    can reference the already-elaborated abstract node and every outer
    flow/claim built from the rest of the module (docs/strata/surface.md
    #refinement). Any abstract node with no matching refine block is left
    untouched -- that is the unrefined frontier, logged at WARNING as the
    planning-frontier signal rather than an error.
    """
    nodes: dict[str, Node] = {n.id: n for n in model.nodes}
    flows: list[Flow] = list(model.flows)
    claims: list[Claim] = list(model.claims)

    for refine in module.refines:
        applied = _apply_refine(refine, nodes, flows, claims)
        if applied.is_err:
            return Err(applied.danger_err)

    for node in nodes.values():
        if _ABSTRACT_ATTR in node.attrs:
            _log.warning(
                "unrefined frontier: node %r is abstract with no refine block", node.id
            )

    return Ok(
        model.model_copy(
            update={
                "nodes": tuple(nodes.values()),
                "flows": tuple(flows),
                "claims": tuple(claims),
            }
        )
    )


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

    infra = elaborate_infra(module, model.nodes, model.flows, model.boundaries)
    if infra.is_err:
        return Err(infra.danger_err)
    expansion = infra.danger_ok
    for diagnostic in expansion.diagnostics:
        _log.warning("std.infra diagnostic: %s", diagnostic)
    model = model.model_copy(
        update={
            "nodes": expansion.nodes,
            "flows": expansion.flows,
            "boundaries": expansion.boundaries,
        }
    )

    refined = _elaborate_refines(module, model)
    if refined.is_err:
        return Err(refined.danger_err)
    model = refined.danger_ok
    _log.info(
        "elaborated module %s: %d node(s), %d flow(s), %d boundary(ies), %d claim(s), "
        "%d refine(s)",
        module.name,
        len(model.nodes),
        len(model.flows),
        len(model.boundaries),
        len(model.claims),
        len(module.refines),
    )
    return Ok(model)
