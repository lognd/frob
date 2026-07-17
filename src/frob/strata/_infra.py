"""std.infra elaborator: store/cache/queue/cdn/balancer -> kernel facts.

A vocabulary is a pure function `surface construct -> kernel facts` (charter
law 1, docs/strata/surface.md#std-infra). `std.infra` is the second
vocabulary after `std.trust` (`_elaborate.py`); it never grows the kernel --
every construct here desugars to `Node`/`Flow`/`Boundary` and nothing else.
Callers pass in the `Node`/`Flow`/`Boundary` facts already produced by
`std.trust` elaboration (the "of"/"provider" references a cache or cdn
declares must resolve against them), and this module returns the full,
merged fact tuples plus any non-fatal diagnostics -- mirroring the
unrefined-frontier pattern in `_elaborate.py`, diagnostics here are logged
at WARNING by the caller rather than folded into the kernel model, since
`KernelModel` (a kernel type) may not grow a vocabulary-specific field.

Deliberate deviation (documented, not silent): the grammar gives `queue`
and `balancer` no `TRUST` clause (unlike `store`/`cache`/`cdn`, which all
have one, declared or inherited). Both default to `"trusted"` here -- see
docs/strata/surface.md#std-infra for the rationale and the follow-up
ticket tracking a grammar extension to make this declared instead of
defaulted.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import BalancerDecl, CacheDecl, CdnDecl, Module, QueueDecl, StoreDecl
from ._errors import StrataError
from ._models import Boundary, BoundaryDirection, Flow, Node, Quantity

_log = get_logger(__name__)

#: Deliberate default trust for queue/balancer nodes; the grammar gives
#: neither construct a TRUST clause (see module docstring).
_INFRA_DEFAULT_TRUST = "trusted"

#: Node attr a sticky balancer's downstream must NOT carry (contradiction).
_STATE_NONE = "state=none"


# frob:doc docs/strata/surface.md#std-infra
class InfraExpansion(BaseModel):
    """The full merged `Node`/`Flow`/`Boundary` tuples after std.infra desugaring.

    WHY a merged (not additive) shape: queue delivery propagation patches
    attrs on flows `std.trust` already produced, so the caller cannot just
    concatenate old and new -- it must take this module's tuples as the new
    truth. `diagnostics` carries non-fatal findings (the sticky-balancer
    contradiction) the caller logs; nothing here is a `KernelModel` field.
    """

    model_config = ConfigDict(frozen=True)

    nodes: tuple[Node, ...] = ()
    flows: tuple[Flow, ...] = ()
    boundaries: tuple[Boundary, ...] = ()
    diagnostics: tuple[str, ...] = ()


def _elaborate_store(decl: StoreDecl) -> Node:
    """`store` -> `Node` at its declared trust; engine/durability become attrs."""
    attrs = list(decl.attrs)
    if decl.engine is not None:
        attrs.append(f"engine={decl.engine}")
    if decl.immutable:
        attrs.append("immutable")
    if decl.append_only:
        attrs.append("append_only")
    _log.debug("store %s -> node at trust %s, attrs=%s", decl.id, decl.trust, attrs)
    return Node(
        id=decl.id,
        trust=decl.trust,
        clearance=decl.clearance,
        attrs=tuple(attrs),
        capacity=None,
        residence=decl.residence,
    )


def _elaborate_queue(decl: QueueDecl) -> Node:
    """`queue` -> `Node`; delivery/ordering become attrs (trust default: module doc)."""
    attrs = list(decl.attrs)
    if decl.delivery is not None:
        attrs.append(f"delivery={decl.delivery}")
    if decl.ordering is not None:
        attrs.append(f"ordering={decl.ordering}")
    _log.warning(
        "queue %s: trust defaulted to %r -- no TRUST clause yet (T-0093)",
        decl.id,
        _INFRA_DEFAULT_TRUST,
    )
    _log.debug("queue %s -> node, attrs=%s", decl.id, attrs)
    return Node(
        id=decl.id,
        trust=_INFRA_DEFAULT_TRUST,
        clearance=decl.clearance or "Secret",
        attrs=tuple(attrs),
    )


def _elaborate_balancer(decl: BalancerDecl) -> Node:
    """`balancer` -> `Node`; policy/sticky become attrs (trust default: module doc)."""
    attrs: list[str] = []
    if decl.policy is not None:
        attrs.append(f"policy={decl.policy}")
    if decl.sticky:
        attrs.append("sticky")
    _log.warning(
        "balancer %s: trust defaulted to %r -- no TRUST clause yet (T-0093)",
        decl.id,
        _INFRA_DEFAULT_TRUST,
    )
    _log.debug("balancer %s -> node, attrs=%s", decl.id, attrs)
    return Node(id=decl.id, trust=_INFRA_DEFAULT_TRUST, attrs=tuple(attrs))


def _elaborate_cache(
    decl: CacheDecl, known: dict[str, Node], base_flows: tuple[Flow, ...]
) -> Result[tuple[Node, tuple[Flow, ...]], StrataError]:
    """`cache X of Y` -> `Node` X + fill flow + mandatory invalidation edges.

    Fails closed (deny by default, docs/strata/surface.md#std-infra):
    unknown `of` target; ttl/staleness both absent, or both present and
    disagreeing (the age collapse -- one bound, not two independent ones);
    an `invalidate_on` naming a flow that does not exist or does not write
    to Y; or Y having any inbound flow at all with no `invalidate_on`
    declared (no cache without an invalidation edge, charter D-age-collapse).
    """
    source = known.get(decl.of)
    if source is None:
        _log.error("cache %s: source-of-truth %r is not declared", decl.id, decl.of)
        return Err(StrataError.UnknownReference)

    bound: object | None = None
    if decl.ttl is not None and decl.staleness is not None:
        ttl_base = decl.ttl.base_value()
        stale_base = decl.staleness.base_value()
        if ttl_base.is_err:
            return Err(ttl_base.danger_err)
        if stale_base.is_err:
            return Err(stale_base.danger_err)
        if ttl_base.danger_ok != stale_base.danger_ok:
            _log.error(
                "cache %s: ttl %s%s disagrees with staleness %s%s",
                decl.id,
                decl.ttl.value,
                decl.ttl.unit,
                decl.staleness.value,
                decl.staleness.unit,
            )
            return Err(StrataError.MissingBound)
        bound = decl.ttl
    elif decl.ttl is not None:
        bound = decl.ttl
    elif decl.staleness is not None:
        bound = decl.staleness
    else:
        _log.error("cache %s: neither ttl nor staleness declared", decl.id)
        return Err(StrataError.MissingBound)

    writes_to_source = [f for f in base_flows if f.dst == decl.of]
    if writes_to_source and not decl.invalidate_on:
        _log.error(
            "cache %s: source %r has inbound write flow(s) %s but no invalidate_on",
            decl.id,
            decl.of,
            [f.id for f in writes_to_source],
        )
        return Err(StrataError.MissingInvalidation)

    inval_flows: list[Flow] = []
    known_flow_ids = {f.id: f for f in base_flows}
    for flow_id in decl.invalidate_on:
        target_flow = known_flow_ids.get(flow_id)
        if target_flow is None:
            _log.error(
                "cache %s: invalidate_on %r is not a declared flow", decl.id, flow_id
            )
            return Err(StrataError.UnknownReference)
        if target_flow.dst != decl.of:
            _log.error(
                "cache %s: invalidate_on %r does not write to source %r",
                decl.id,
                flow_id,
                decl.of,
            )
            return Err(StrataError.MissingInvalidation)
        inval_flows.append(
            Flow(
                id=f"{decl.id}__inval_{flow_id}",
                src=decl.of,
                dst=decl.id,
                age=Quantity(value=0.0, unit="s"),
                attrs=("invalidation",),
            )
        )

    node_attrs: list[str] = []
    if decl.hit is not None:
        node_attrs.append(f"hit={decl.hit}")
    if decl.policy is not None:
        node_attrs.append(f"policy={decl.policy}")
    if decl.keyed_by is not None:
        node_attrs.append(f"keyed_by={decl.keyed_by}")

    node = Node(
        id=decl.id,
        trust=source.trust,
        clearance=source.clearance,
        attrs=tuple(node_attrs),
    )
    fill_flow = Flow(
        id=f"{decl.id}__fill",
        src=decl.of,
        dst=decl.id,
        label=source.clearance,
        age=bound,  # type: ignore[arg-type]
        attrs=("fill",),
    )
    _log.debug(
        "cache %s of %s -> node + fill flow (age=%s) + %d invalidation edge(s)",
        decl.id,
        decl.of,
        bound,
        len(inval_flows),
    )
    return Ok((node, (fill_flow, *inval_flows)))


def _elaborate_cdn(
    decl: CdnDecl, known: dict[str, Node]
) -> Result[tuple[Node, Flow, tuple[Boundary, ...]], StrataError]:
    """`cdn X of Y` -> `Node` X + fill flow (+ declassify boundary when TLS terminates).

    Fails closed: unknown `of` target; no provider (and thus no provider
    trust) declared -- law 2, no security defaults; and `staleness
    unlimited` declared over a source that is not marked `immutable` (the
    immutable-TTL pairing -- unbounded staleness is only safe when the
    source never changes).
    """
    source = known.get(decl.of)
    if source is None:
        _log.error("cdn %s: source-of-truth %r is not declared", decl.id, decl.of)
        return Err(StrataError.UnknownReference)
    if decl.provider is None or decl.provider_trust is None:
        _log.error("cdn %s: no provider (with trust) declared", decl.id)
        return Err(StrataError.MissingBound)

    age = None
    if decl.staleness_unlimited:
        if "immutable" not in source.attrs:
            _log.error(
                "cdn %s: staleness unlimited over mutable source %r "
                "(not marked immutable)",
                decl.id,
                decl.of,
            )
            return Err(StrataError.MutableUnbounded)
        _log.debug(
            "cdn %s: staleness unlimited over immutable source %r -- age=0",
            decl.id,
            decl.of,
        )
    elif decl.staleness is not None:
        age = decl.staleness
    else:
        _log.error("cdn %s: no staleness bound declared", decl.id)
        return Err(StrataError.MissingBound)

    node_attrs: list[str] = [f"provider={decl.provider}"]
    if decl.hit is not None:
        node_attrs.append(f"hit={decl.hit}")

    node = Node(
        id=decl.id,
        trust=decl.provider_trust,
        clearance=source.clearance,
        attrs=tuple(node_attrs),
    )
    fill_flow = Flow(
        id=f"{decl.id}__fill",
        src=decl.of,
        dst=decl.id,
        label=source.clearance,
        age=age,
        attrs=("fill",),
    )
    boundaries: tuple[Boundary, ...] = ()
    if decl.tls_terminates_at_provider:
        boundaries = (
            Boundary(
                id=f"{decl.id}__declassify",
                flow_id=fill_flow.id,
                direction=BoundaryDirection.DECLASSIFY,
                from_level=source.clearance,
                to_level="Public",
                predicate="tls_terminates_at_provider",
            ),
        )
        _log.debug(
            "cdn %s: tls_terminates_at_provider -> declassify boundary on %s",
            decl.id,
            fill_flow.id,
        )
    return Ok((node, fill_flow, boundaries))


def _propagate_queue_delivery(
    flows: tuple[Flow, ...], queue_delivery: dict[str, str]
) -> tuple[Flow, ...]:
    """Every outbound flow from a queue node gains that queue's `delivery=<x>` attr.

    WHY: this is what lets `_facts.py`'s existing at-least-once diagnostic
    fire on the queue's consumers without the fact base ever learning the
    word "queue" -- the attr is the only channel (docs/strata/surface.md
    #std-infra).
    """
    patched: list[Flow] = []
    for flow in flows:
        delivery = queue_delivery.get(flow.src)
        attr = f"delivery={delivery}" if delivery is not None else None
        if attr is not None and attr not in flow.attrs:
            _log.debug(
                "queue %s: propagating %s onto outbound flow %s",
                flow.src,
                attr,
                flow.id,
            )
            patched.append(flow.model_copy(update={"attrs": (*flow.attrs, attr)}))
        else:
            patched.append(flow)
    return tuple(patched)


def _sticky_balancer_diagnostics(
    balancers: tuple[BalancerDecl, ...], nodes: dict[str, Node], flows: tuple[Flow, ...]
) -> tuple[str, ...]:
    """A sticky balancer routing to a `state=none` downstream is a contradiction."""
    findings: list[str] = []
    for decl in balancers:
        if not decl.sticky:
            continue
        downstream_ids = {f.dst for f in flows if f.src == decl.id}
        for dst_id in sorted(downstream_ids):
            dst = nodes.get(dst_id)
            if dst is not None and _STATE_NONE in dst.attrs:
                finding = (
                    f"balancer {decl.id}: sticky routing to stateless downstream "
                    f"{dst_id} ({_STATE_NONE})"
                )
                findings.append(finding)
    for finding in findings:
        _log.warning("std.infra: %s", finding)
    return tuple(findings)


# frob:doc docs/strata/surface.md#std-infra
def elaborate_infra(
    module: Module,
    nodes: tuple[Node, ...],
    flows: tuple[Flow, ...],
    boundaries: tuple[Boundary, ...],
) -> Result[InfraExpansion, StrataError]:
    """Desugar every std.infra construct in `module` into kernel facts.

    WHY this signature: `_elaborate.py::elaborate` calls this after the
    `std.trust` mapping (nodes/flows/boundaries already built from
    `NodeDecl`/`FlowDecl`/`BoundaryDecl`) so `cache`/`cdn` "of" references
    and the mandatory-invalidation check can resolve against real facts.
    The result replaces (not appends to) the caller's tuples, since queue
    delivery propagation patches attrs on flows that already existed.
    """
    known: dict[str, Node] = {n.id: n for n in nodes}

    new_nodes: list[Node] = []
    for store in module.stores:
        new_nodes.append(_elaborate_store(store))
    for queue in module.queues:
        new_nodes.append(_elaborate_queue(queue))
    for balancer in module.balancers:
        new_nodes.append(_elaborate_balancer(balancer))
    for n in new_nodes:
        known[n.id] = n

    new_flows: list[Flow] = []
    new_boundaries: list[Boundary] = []
    for cache in module.caches:
        result = _elaborate_cache(cache, known, flows)
        if result.is_err:
            return Err(result.danger_err)
        node, cache_flows = result.danger_ok
        new_nodes.append(node)
        known[node.id] = node
        new_flows.extend(cache_flows)

    for cdn in module.cdns:
        result = _elaborate_cdn(cdn, known)
        if result.is_err:
            return Err(result.danger_err)
        node, fill_flow, cdn_boundaries = result.danger_ok
        new_nodes.append(node)
        known[node.id] = node
        new_flows.append(fill_flow)
        new_boundaries.extend(cdn_boundaries)

    queue_delivery = {q.id: q.delivery for q in module.queues if q.delivery is not None}
    all_flows = _propagate_queue_delivery((*flows, *new_flows), queue_delivery)

    diagnostics = _sticky_balancer_diagnostics(module.balancers, known, all_flows)

    all_nodes = (*nodes, *new_nodes)
    all_boundaries = (*boundaries, *new_boundaries)

    _log.info(
        "elaborated std.infra for module %s: %d store(s), %d cache(s), %d queue(s), "
        "%d cdn(s), %d balancer(s), %d diagnostic(s)",
        module.name,
        len(module.stores),
        len(module.caches),
        len(module.queues),
        len(module.cdns),
        len(module.balancers),
        len(diagnostics),
    )
    return Ok(
        InfraExpansion(
            nodes=all_nodes,
            flows=all_flows,
            boundaries=all_boundaries,
            diagnostics=diagnostics,
        )
    )
