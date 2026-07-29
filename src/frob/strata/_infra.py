"""std.infra elaborator: store/cache/queue/cdn/balancer -> kernel facts.

A vocabulary is a pure function `surface construct -> kernel facts` (charter
law 1, docs/strata/surface.md#stdinfra). `std.infra` is the second
vocabulary after `std.trust` (`_elaborate.py`); it never grows the kernel --
every construct here desugars to `Node`/`Flow`/`Boundary` and nothing else.
Callers pass in the `Node`/`Flow`/`Boundary` facts already produced by
`std.trust` elaboration (the "of"/"provider" references a cache or cdn
declares must resolve against them), and this module returns the full,
merged fact tuples plus any non-fatal diagnostics -- mirroring the
unrefined-frontier pattern in `_elaborate.py`, diagnostics here are logged
at WARNING by the caller rather than folded into the kernel model, since
`KernelModel` (a kernel type) may not grow a vocabulary-specific field.

`queue` and `balancer` now accept an optional `TRUST` clause (T-0093,
`queue X : TRUST { ... }` / `balancer X : TRUST { ... }`), matching
`store`/`cache`/`cdn`. When the clause is omitted the elaborator still
falls back to the documented `"trusted"` default below -- a declared
deviation, not a silent one (docs/strata/surface.md#stdinfra).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import (
    BalancerDecl,
    CacheDecl,
    CdnDecl,
    Module,
    QueueDecl,
    StoreDecl,
    _DeployDecl,
)
from ._code_binding import _CODE_PREFIX
from ._errors import StrataError
from ._host import _host_attrs
from ._models import (
    Boundary,
    BoundaryDirection,
    CanaryStage,
    DeployContract,
    Flow,
    Node,
    Quantity,
    Waiver,
)
from ._models import Capacity as KernelCapacity
from ._pii import _PII_PREFIX
from ._waive import _validate_waiver_fields

_log = get_logger(__name__)

#: Deliberate default trust for queue/balancer nodes; the grammar gives
#: neither construct a TRUST clause (see module docstring).
_INFRA_DEFAULT_TRUST = "trusted"

#: Node attr a sticky balancer's downstream must NOT carry (contradiction).
_STATE_NONE = "state=none"

#: Node attr marker for `managed` stores (T-0172), the SAME literal
#: `_elaborate.py::_MANAGED_ATTR` uses for `node` -- kept as a local
#: literal rather than an import to avoid a cycle (`_elaborate.py` already
#: imports THIS module for `elaborate_infra`).
_MANAGED_ATTR = "managed"

#: Node attr marker for a store's `errors_total` claim (T-0247), the SAME
#: literal `_elaborate.py::_ERRORS_TOTAL_ATTR` uses for `node` -- kept
#: local for the same import-cycle reason as `_MANAGED_ATTR` above.
_ERRORS_TOTAL_ATTR = "errors_total"

#: Flow attr marking a `cache`'s elaborator-synthesized fill/invalidation
#: edges as explicitly NOT crossing a real process/service boundary
#: (T-0845, the SAME bare-marker literal `_reliability.py::_LOCAL_ATTR`
#: reads to exempt a flow from the REL200 TIMEOUT obligation -- kept as a
#: local copy, not an import, for the same cross-module-vocabulary reason
#: `_MANAGED_ATTR` above documents). This is a deliberate, unconditional
#: disposition for the `cache` construct specifically (NOT `cdn`): per
#: docs/strata/surface.md#key-construct-semantics, `cache X of Y` is
#: std.infra's IN-PROCESS derived view -- its node inherits `Y`'s own
#: trust directly (`_cache_node_and_fill_flow` below) rather than a
#: separate provider trust the way `cdn`'s network-fronting variant does
#: (`_cdn_node_and_fill_flow`, which deliberately does NOT get this attr).
#: `cache` therefore has no real cross-boundary hop to time-bound in the
#: first place, for EVERY declaration of it, not just this repo's own
#: `graph_cache` -- this is the "explicit local disposition for
#: in-process in-memory flows" T-0845 chose over a per-flow `attr`
#: grammar clause, since `cache`'s parser (`strata-core::parse_cache`)
#: has no such clause and adding one is a strata-core change outside this
#: ticket's scope (src/frob/strata/**, design/frob.strata,
#: tests/unit/strata/** only).
_CACHE_LOCAL_ATTR = "local"


def _elaborate_store_deploy(decl: _DeployDecl) -> DeployContract:
    """One store's `_DeployDecl` -> `DeployContract` (T-0247), the SAME
    field-for-field mapping `_elaborate.py::_elaborate_deploy` uses for
    `node` -- duplicated locally for the same import-cycle reason as
    `_MANAGED_ATTR` above."""
    return DeployContract(
        stages=tuple(
            CanaryStage(level=s.level, bake=s.bake, max_error_rate=None)
            for s in decl.stages
        ),
        endorsement_chain=decl.endorsed_by,
        rollback_budget=decl.rollback_budget,
    )


# frob:doc docs/strata/surface.md#stdinfra
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


def _elaborate_store(decl: StoreDecl) -> Result[Node, StrataError]:
    """`store` -> `Node` at its declared trust; engine/durability/rpo become
    attrs (rpo unit-dimension check: `_store_rpo_attr`; code/may desugar
    precedent: `_store_base_attrs`); errors_total/panics_contained_by ->
    attrs and `on deploy` -> `Node.deploy` directly (T-0247, same desugar
    `_elaborate.py::_elaborate_node` uses for `node`)."""
    attrs_result = _store_attrs(decl)
    if attrs_result.is_err:
        return Err(attrs_result.danger_err)
    waives_result = _validate_store_waives(decl)
    if waives_result.is_err:
        return Err(waives_result.danger_err)
    deploy = None if decl.deploy is None else _elaborate_store_deploy(decl.deploy)
    _log.debug(
        "store %s -> node at trust %s, attrs=%s",
        decl.id,
        decl.trust,
        attrs_result.danger_ok,
    )
    return Ok(
        Node(
            id=decl.id,
            trust=decl.trust,
            clearance=decl.clearance,
            may=decl.may,
            attrs=tuple(attrs_result.danger_ok),
            capacity=_store_capacity(decl),
            users=decl.users,
            rate=decl.rate,
            residence=decl.residence,
            deploy=deploy,
            waives=waives_result.danger_ok,
        )
    )


def _store_attrs(decl: StoreDecl) -> Result[list[str], StrataError]:
    """`_store_base_attrs` plus the `rpo=<seconds>` attr, or the fail-closed
    `Err` `_store_rpo_attr` returns for a non-time-unit `rpo`."""
    attrs = _store_base_attrs(decl)
    rpo_attr = _store_rpo_attr(decl)
    if rpo_attr.is_err:
        return Err(rpo_attr.danger_err)
    if rpo_attr.danger_ok is not None:
        attrs.append(rpo_attr.danger_ok)
    return Ok(attrs)


def _store_base_attrs(decl: StoreDecl) -> list[str]:
    """The non-fallible attr list a `store` desugars to before rpo/waives:
    carries/code/engine/immutable/append_only/managed/errors_total/panics/
    host attrs, in declaration order (T-0154/T-0166/T-0172/T-0247/T-0255
    desugar precedents, each documented inline below)."""
    attrs = list(decl.attrs)
    attrs.extend(_store_carries_code_attrs(decl))
    if decl.engine is not None:
        attrs.append(f"engine={decl.engine}")
    if decl.immutable:
        attrs.append("immutable")
    if decl.append_only:
        attrs.append("append_only")
    if decl.is_managed:
        # T-0172: config-only infra store -- no `code=` glob expected.
        _log.debug("store %s is managed; marking attrs with %r", decl.id, _MANAGED_ATTR)
        attrs.append(_MANAGED_ATTR)
    if decl.errors_total:
        # T-0247: same bare-marker desugar `_elaborate.py::
        # _node_marker_attrs` uses for `node`'s `errors_total` clause.
        _log.debug("store %s declares errors_total", decl.id)
        attrs.append(_ERRORS_TOTAL_ATTR)
    if decl.panics_contained_by is not None:
        # T-0247: same `panics=<id>` attr desugar `node` gets; reference
        # validity is checked by `_elaborate.py::_validate_observability`
        # (which now also walks `module.stores`).
        _log.debug(
            "store %s: panics contained by %s", decl.id, decl.panics_contained_by
        )
        attrs.append(f"panics={decl.panics_contained_by}")
    attrs.extend(_store_host_attrs(decl))
    return attrs


def _store_carries_code_attrs(decl: StoreDecl) -> list[str]:
    """T-0154 `pii=<tag>` and T-0166 `code=<glob>` attrs for a `store`'s
    `carries`/`code` clauses -- the SAME per-atom desugars `_elaborate.py
    ::_elaborate_node` uses for `node` (`_pii.py::node_pii_tags` and
    `_code_binding.py::_node_code_globs` read them back off ANY elaborated
    `Node`, store-derived or not)."""
    attrs: list[str] = []
    if decl.carries:
        _log.debug("store %s carries %d pii tag(s)", decl.id, len(decl.carries))
        attrs.extend(f"{_PII_PREFIX}{tag}" for tag in decl.carries)
    if decl.code:
        _log.debug("store %s declares %d code glob(s)", decl.id, len(decl.code))
        attrs.extend(f"{_CODE_PREFIX}{glob}" for glob in decl.code)
    return attrs


def _store_host_attrs(decl: StoreDecl) -> tuple[str, ...]:
    """T-0255 std.host attrs for a `store` -- same shared `_host.py::
    _host_attrs` encoding `_elaborate.py::_elaborate_node` uses for `node`.
    `group`/`sudoers` (T-0272) and `platform`/`service_account`/`service`/
    `acl`/`pipes` (T-0261) pass through the same way."""
    host = _host_attrs(
        runs_as=decl.runs_as,
        is_unit=decl.is_unit,
        owns=tuple((o.path, o.mode) for o in decl.owns),
        listens=decl.listens,
        group=decl.group,
        sudoers=decl.sudoers,
        platform=decl.platform,
        service_account=decl.service_account,
        service_account_gmsa=decl.service_account_gmsa,
        is_service=decl.is_service,
        acl=tuple((a.path, a.rule) for a in decl.acl),
        pipes=decl.pipes,
    )
    if host:
        _log.debug("store %s declares %d std.host attr(s)", decl.id, len(host))
    return host


def _store_rpo_attr(decl: StoreDecl) -> Result[str | None, StrataError]:
    """The `rpo=<seconds>` attr for a `store`'s declared `rpo`, or `None`
    if none was declared.

    `rpo` is the store's declared durability/replication lag -- the same
    age-collapse family as cache ttl (docs/strata/kernel.md#age-propagation-
    semantics). The grammar accepts any unit; this fails closed if it is
    not a time unit (deny by default, no silent dimension coercion).
    """
    if decl.rpo is None:
        return Ok(None)
    dimension = decl.rpo.dimension()
    if dimension.is_err:
        _log.error("store %s: rpo has unknown unit %r", decl.id, decl.rpo.unit)
        return Err(dimension.danger_err)
    if dimension.danger_ok != "time":
        _log.error(
            "store %s: rpo %s%s is not a time unit",
            decl.id,
            decl.rpo.value,
            decl.rpo.unit,
        )
        return Err(StrataError.UnitMismatch)
    seconds = decl.rpo.base_value().danger_ok
    return Ok(f"rpo={seconds}")


def _store_capacity(decl: StoreDecl) -> KernelCapacity | None:
    """The kernel `Capacity` a `store`'s declared `capacity` maps to
    (T-0103), or `None` if none was declared."""
    if decl.capacity is None:
        return None
    capacity = KernelCapacity(
        service_rate=decl.capacity.rate,
        replicas_min=decl.capacity.replicas_min,
        replicas_max=decl.capacity.replicas_max,
    )
    _log.debug("store %s: declared capacity mapped through (T-0103)", decl.id)
    return capacity


# T-0250: `waive RULE reason="..." [ticket="..."]`+ desugars the SAME
# direct-mapping way `_elaborate.py::_elaborate_node` desugars them for
# `node` -- straight to `Node.waives`, so a store's declared waiver
# discharges a `frob sys audit` finding against it exactly like a
# node's would (`_waive.py` reads `Node.waives` generically off any
# elaborated `Node`, with no store/node distinction).
#
# `_elaborate.py::_validate_waivers` only walks `module.nodes` (it runs
# BEFORE `elaborate_infra`/`_elaborate_store` even sees `module.stores`,
# `_elaborate.py::elaborate`'s call order) -- a store's `waive` clause
# would silently skip the mandatory-non-blank-reason and multi-instance
# sub-target check `_validate_waivers` gives `node` unless this
# elaborator enforces it itself. Same check, same error, just run here
# instead, so the T-0174 "no way to elaborate a blank-reason waiver"
# guarantee (docs/strata/waive.md) holds for stores too.
def _validate_store_waives(
    decl: StoreDecl,
) -> Result[tuple[Waiver, ...], StrataError]:
    """Validate and desugar a `store`'s `waive` clauses to `Waiver`s,
    failing closed on the first malformed clause (see the module note
    above `_validate_store_waives` for why this duplicates `_elaborate.py
    ::_validate_waivers`'s check rather than reusing it)."""
    for w in decl.waives:
        checked = _validate_waiver_fields(w.rule, w.reason)
        if checked.is_err:
            _log.error(
                "store %s: malformed waive clause rule=%r reason=%r",
                decl.id,
                w.rule,
                w.reason,
            )
            return Err(checked.danger_err)
    return Ok(
        tuple(
            Waiver(rule=w.rule, reason=w.reason, ticket=w.ticket) for w in decl.waives
        )
    )


def _elaborate_queue(decl: QueueDecl) -> Node:
    """`queue` -> `Node`; delivery/ordering become attrs, trust explicit or defaulted.

    T-0093: `decl.trust` is `None` unless the source declares `queue X :
    TRUST`, in which case it wins over the documented `"trusted"` default
    (module docstring, docs/strata/surface.md#stdinfra deviation note).
    """
    attrs = list(decl.attrs)
    if decl.delivery is not None:
        attrs.append(f"delivery={decl.delivery}")
    if decl.ordering is not None:
        attrs.append(f"ordering={decl.ordering}")
    if decl.trust is None:
        _log.warning(
            "queue %s: trust defaulted to %r -- no TRUST clause declared (T-0093)",
            decl.id,
            _INFRA_DEFAULT_TRUST,
        )
    trust = decl.trust or _INFRA_DEFAULT_TRUST
    _log.debug("queue %s -> node at trust %s, attrs=%s", decl.id, trust, attrs)
    return Node(
        id=decl.id,
        trust=trust,
        clearance=decl.clearance or "Secret",
        attrs=tuple(attrs),
    )


def _elaborate_balancer(decl: BalancerDecl) -> Node:
    """`balancer` -> `Node`; policy/sticky become attrs; trust is explicit or defaulted.

    T-0093: `decl.trust` is `None` unless the source declares `balancer X :
    TRUST`, in which case it wins over the documented `"trusted"` default
    (module docstring, docs/strata/surface.md#stdinfra deviation note).
    """
    attrs: list[str] = []
    if decl.policy is not None:
        attrs.append(f"policy={decl.policy}")
    if decl.sticky:
        attrs.append("sticky")
    if decl.trust is None:
        _log.warning(
            "balancer %s: trust defaulted to %r -- no TRUST clause declared (T-0093)",
            decl.id,
            _INFRA_DEFAULT_TRUST,
        )
    trust = decl.trust or _INFRA_DEFAULT_TRUST
    _log.debug("balancer %s -> node at trust %s, attrs=%s", decl.id, trust, attrs)
    return Node(id=decl.id, trust=trust, attrs=tuple(attrs))


def _cache_bound(decl: CacheDecl) -> Result[Quantity, StrataError]:
    """The ttl/staleness age bound a `cache` collapses to a single
    `Quantity` -- one bound, not two independent ones (charter D-age-
    collapse). Fails closed if both are declared and disagree, or if
    neither is declared."""
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
        return Ok(decl.ttl)
    if decl.ttl is not None:
        return Ok(decl.ttl)
    if decl.staleness is not None:
        return Ok(decl.staleness)
    _log.error("cache %s: neither ttl nor staleness declared", decl.id)
    return Err(StrataError.MissingBound)


def _cache_invalidation_flows(
    decl: CacheDecl, base_flows: tuple[Flow, ...]
) -> Result[list[Flow], StrataError]:
    """The invalidation `Flow`s a `cache`'s `invalidate_on` clauses desugar
    to. Fails closed if the source has an inbound write flow with no
    `invalidate_on` at all, or if any named flow does not exist or does
    not write to the source (no cache without an invalidation edge,
    charter D-age-collapse)."""
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
        flow_result = _cache_invalidation_flow_for(decl, known_flow_ids, flow_id)
        if flow_result.is_err:
            return Err(flow_result.danger_err)
        inval_flows.append(flow_result.danger_ok)
    return Ok(inval_flows)


def _cache_invalidation_flow_for(
    decl: CacheDecl, known_flow_ids: dict[str, Flow], flow_id: str
) -> Result[Flow, StrataError]:
    """The single invalidation `Flow` for one `invalidate_on` reference,
    or the fail-closed `Err` if it does not name a declared flow that
    writes to the cache's source (see `_cache_invalidation_flows`).
    Carries `_CACHE_LOCAL_ATTR` (T-0845): an in-process cache invalidation
    edge, exempt from REL200's cross-boundary TIMEOUT obligation by
    construction (see that constant's docstring)."""
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
    return Ok(
        Flow(
            id=f"{decl.id}__inval_{flow_id}",
            src=decl.of,
            dst=decl.id,
            age=Quantity(value=0.0, unit="s"),
            attrs=("invalidation", _CACHE_LOCAL_ATTR),
        )
    )


def _elaborate_cache(
    decl: CacheDecl, known: dict[str, Node], base_flows: tuple[Flow, ...]
) -> Result[tuple[Node, tuple[Flow, ...]], StrataError]:
    """`cache X of Y` -> `Node` X + fill flow + mandatory invalidation edges.
    Fails closed on an unknown `of` target, an unresolvable age bound
    (`_cache_bound`), or a missing/invalid invalidation edge
    (`_cache_invalidation_flows`) -- docs/strata/surface.md#stdinfra."""
    source = known.get(decl.of)
    if source is None:
        _log.error("cache %s: source-of-truth %r is not declared", decl.id, decl.of)
        return Err(StrataError.UnknownReference)

    bound_result = _cache_bound(decl)
    if bound_result.is_err:
        return Err(bound_result.danger_err)
    bound = bound_result.danger_ok

    inval_result = _cache_invalidation_flows(decl, base_flows)
    if inval_result.is_err:
        return Err(inval_result.danger_err)
    inval_flows = inval_result.danger_ok

    node, fill_flow = _cache_node_and_fill_flow(decl, source, bound)
    _log.debug(
        "cache %s of %s -> node + fill flow (age=%s) + %d invalidation edge(s)",
        decl.id,
        decl.of,
        bound,
        len(inval_flows),
    )
    return Ok((node, (fill_flow, *inval_flows)))


def _cache_node_and_fill_flow(
    decl: CacheDecl, source: Node, bound: Quantity
) -> tuple[Node, Flow]:
    """The `Node` + fill `Flow` a `cache` desugars to, given its resolved
    source-of-truth `Node` and age `bound` (see `_elaborate_cache`). The
    fill flow carries `_CACHE_LOCAL_ATTR` (T-0845): see that constant's
    docstring for why every `cache` fill edge is exempt from REL200's
    cross-boundary TIMEOUT obligation by construction."""
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
        attrs=("fill", _CACHE_LOCAL_ATTR),
    )
    return node, fill_flow


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

    age_result = _cdn_age(decl, source)
    if age_result.is_err:
        return Err(age_result.danger_err)

    node, fill_flow = _cdn_node_and_fill_flow(
        decl, source, decl.provider_trust, age_result.danger_ok
    )
    boundaries = _cdn_boundaries(decl, source, fill_flow)
    return Ok((node, fill_flow, boundaries))


def _cdn_age(decl: CdnDecl, source: Node) -> Result[Quantity | None, StrataError]:
    """The fill-flow age for a `cdn`: `None` (age=0, unbounded) if
    `staleness unlimited` over an `immutable` source, else the declared
    `staleness`. Fails closed on unlimited staleness over a mutable
    source, or no staleness bound at all (see `_elaborate_cdn`)."""
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
        return Ok(None)
    if decl.staleness is not None:
        return Ok(decl.staleness)
    _log.error("cdn %s: no staleness bound declared", decl.id)
    return Err(StrataError.MissingBound)


def _cdn_node_and_fill_flow(
    decl: CdnDecl, source: Node, provider_trust: str, age: Quantity | None
) -> tuple[Node, Flow]:
    """The `Node` + fill `Flow` a `cdn` desugars to (see `_elaborate_cdn`).
    `provider_trust` is passed narrowed (non-`None`) by the caller, which
    already fails closed on a missing provider trust."""
    node_attrs: list[str] = [f"provider={decl.provider}"]
    if decl.hit is not None:
        node_attrs.append(f"hit={decl.hit}")

    node = Node(
        id=decl.id,
        trust=provider_trust,
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
    return node, fill_flow


def _cdn_boundaries(
    decl: CdnDecl, source: Node, fill_flow: Flow
) -> tuple[Boundary, ...]:
    """The declassify `Boundary` a `cdn`'s `tls_terminates_at_provider`
    clause desugars to, or `()` if the clause is absent."""
    if not decl.tls_terminates_at_provider:
        return ()
    _log.debug(
        "cdn %s: tls_terminates_at_provider -> declassify boundary on %s",
        decl.id,
        fill_flow.id,
    )
    return (
        Boundary(
            id=f"{decl.id}__declassify",
            flow_id=fill_flow.id,
            direction=BoundaryDirection.DECLASSIFY,
            from_level=source.clearance,
            to_level="Public",
            predicate="tls_terminates_at_provider",
        ),
    )


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


# frob:ticket T-0148
# frob:ticket T-0972
def _sticky_balancer_diagnostics(
    balancers: tuple[BalancerDecl, ...], nodes: dict[str, Node], flows: tuple[Flow, ...]
) -> tuple[str, ...]:
    """A sticky balancer routing to a `state=none` downstream is a contradiction."""
    findings: list[str] = []
    downstream_by_src: dict[str, set[str]] = {}
    for flow in flows:
        downstream_by_src.setdefault(flow.src, set()).add(flow.dst)
    for decl in balancers:
        if not decl.sticky:
            continue
        downstream_ids = downstream_by_src.get(decl.id, set())
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


def _elaborate_simple_infra_nodes(module: Module) -> Result[list[Node], StrataError]:
    """`store`/`queue`/`balancer` -> `Node`s, in that order -- the
    fallible-then-infallible constructs `elaborate_infra` elaborates
    before any cache/cdn "of" reference needs to resolve against them."""
    new_nodes: list[Node] = []
    for store in module.stores:
        store_result = _elaborate_store(store)
        if store_result.is_err:
            return Err(store_result.danger_err)
        new_nodes.append(store_result.danger_ok)
    for queue in module.queues:
        new_nodes.append(_elaborate_queue(queue))
    for balancer in module.balancers:
        new_nodes.append(_elaborate_balancer(balancer))
    return Ok(new_nodes)


def _elaborate_cache_cdn_nodes(
    module: Module, known: dict[str, Node], flows: tuple[Flow, ...]
) -> Result[tuple[list[Node], list[Flow], list[Boundary]], StrataError]:
    """`cache`/`cdn` -> `Node`s + their fill/invalidation flows and
    declassify boundaries, in that order, resolving "of" references
    against `known` as each new node is elaborated (see `elaborate_infra`)."""
    new_nodes: list[Node] = []
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

    return Ok((new_nodes, new_flows, new_boundaries))


def _elaborate_all_infra_nodes(
    module: Module, known: dict[str, Node], flows: tuple[Flow, ...]
) -> Result[tuple[list[Node], list[Flow], list[Boundary]], StrataError]:
    """Every std.infra node (store/queue/balancer, then cache/cdn) plus
    their new flows/boundaries, mutating `known` in place as each new
    node resolves so later "of" references see it (see `elaborate_infra`)."""
    simple_result = _elaborate_simple_infra_nodes(module)
    if simple_result.is_err:
        return Err(simple_result.danger_err)
    new_nodes = simple_result.danger_ok
    for n in new_nodes:
        known[n.id] = n

    resolved_result = _elaborate_cache_cdn_nodes(module, known, flows)
    if resolved_result.is_err:
        return Err(resolved_result.danger_err)
    resolved_nodes, new_flows, new_boundaries = resolved_result.danger_ok
    for node in resolved_nodes:
        new_nodes.append(node)
        known[node.id] = node

    return Ok((new_nodes, new_flows, new_boundaries))


# frob:doc docs/strata/surface.md#stdinfra
def elaborate_infra(
    module: Module,
    nodes: tuple[Node, ...],
    flows: tuple[Flow, ...],
    boundaries: tuple[Boundary, ...],
) -> Result[InfraExpansion, StrataError]:
    """Desugar every std.infra construct in `module` into kernel facts.
    Called after the `std.trust` mapping so `cache`/`cdn` "of" references
    resolve against real facts; the result REPLACES (not appends to) the
    caller's tuples, since queue delivery propagation patches attrs on
    flows that already existed."""
    known: dict[str, Node] = {n.id: n for n in nodes}

    all_nodes_result = _elaborate_all_infra_nodes(module, known, flows)
    if all_nodes_result.is_err:
        return Err(all_nodes_result.danger_err)
    new_nodes, new_flows, new_boundaries = all_nodes_result.danger_ok

    queue_delivery = {q.id: q.delivery for q in module.queues if q.delivery is not None}
    all_flows = _propagate_queue_delivery((*flows, *new_flows), queue_delivery)

    diagnostics = _sticky_balancer_diagnostics(module.balancers, known, all_flows)

    all_nodes = (*nodes, *new_nodes)
    all_boundaries = (*boundaries, *new_boundaries)
    return Ok(
        _finish_infra_expansion(
            module, all_nodes, all_flows, all_boundaries, diagnostics
        )
    )


def _finish_infra_expansion(
    module: Module,
    all_nodes: tuple[Node, ...],
    all_flows: tuple[Flow, ...],
    all_boundaries: tuple[Boundary, ...],
    diagnostics: tuple[str, ...],
) -> InfraExpansion:
    """Log the elaboration summary and build the final `InfraExpansion`
    (see `elaborate_infra`)."""
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
    return InfraExpansion(
        nodes=all_nodes,
        flows=all_flows,
        boundaries=all_boundaries,
        diagnostics=diagnostics,
    )
