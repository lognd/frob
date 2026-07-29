"""`std.lint`: operational design lints -- caching, resource bounds,
rate-limiting, and kill-switch rules over the kernel model (T-0155,
docs/strata/threat.md#operational-design-lints-stdlint-t-0155,
docs/strata/surface.md#node-grammar).

INVESTIGATED FIRST (T-0150/T-0154 lesson: reuse, never parallel-build):
the scenario engine (`_scenarios.py`, node loss/rate surge/trust
downgrade, T-0073) already re-checks nested claims under a `ScaleRate`
rewrite; `Node.capacity` (`_models.py::Capacity`) already carries a
declared service rate + replica range (T-0103); `Flow.rate` (a `Quantity`)
already carries a declared throughput; `std.infra`'s `cache X of Y`
(`_infra.py::_elaborate_cache`) already produces a `fill` flow from the
cached node; `Node.may` capability atoms + `_effects.py::_may_kind`
already classify exec/net/fs capability kinds (T-0150). Every LINT rule
below is a JOIN over these already-shipped facts -- zero new kernel
primitive (charter law 1), and the one new surface vocabulary word this
module needs (a kill-switch reference) reuses the generic `attr
IDENT=IDENT` node property the grammar already has, the SAME attr-desugar
convention `code=`/`pii=` established (T-0132/T-0154), not a new keyword.

- LINT001 (undeclared rate limit on an external-facing edge): a flow
  sourced from a `foreign`-trust node with no declared `rate` -- the
  kernel's `Flow.rate` field IS the rate-limit declaration (there is no
  separate "rate limit" primitive to invent), so an external-facing flow
  with `rate=None` is a public/edge boundary accepting external input
  with no declared throughput bound at all. Deny-by-default, no claim
  override: a missing rate is a missing FACT, not a risk somebody can
  assume away (the same no-override shape PII001's malformed-category
  check has -- fix the declaration, not the model's threat posture).
- LINT002 (store overload without a caching escape valve): a node with a
  declared `capacity.service_rate` whose non-infra inbound flows'
  combined declared rate exceeds that service rate, AND no `cache`
  construct (`_infra.py`) declared over it (no `fill`-attr flow sourced
  from this node) -- a store being asked to serve more than it declared
  it can, with no caching relief in the picture. `fill`/`invalidation`
  flows are excluded from the summed load since they are the caching
  layer's OWN traffic against the source of truth, not client demand.
- LINT003 (surge scenario with no capacity bound): a `Scenario` containing
  a `ScaleRate` rewrite on flow `F`, where neither `F`'s endpoints nor `F`
  itself is the `target` of a nested `BoundClaim` (`metric` RATE or
  UTILIZATION) inside that SAME scenario -- the scenario engine already
  re-checks nested claims under the rewrite (`_scenarios.py`); this rule
  only asks that a surge scenario actually HAVE something to re-check.
  Structural presence check only (asserted or assumed both count -- an
  author choosing to assert rather than assume a capacity bound is not a
  lint failure, only an absent claim is).
- LINT004 (risky capability with no kill-switch): a node holding a `may`
  atom whose kind (`_effects.py::_may_kind`) is in `RISKY_CAPABILITY_
  KINDS` (exec/net, T-0150's tier-1 capability classes -- code execution
  and outbound network are the two capability kinds an operator can
  plausibly need to kill live, unlike e.g. `fs` reads) with no declared
  `flag=<id>` attr -- reusing the generic `attr IDENT=IDENT` node
  property (module docstring), NOT a new grammar keyword. `flag=<id>`
  names the feature-flag/kill-switch identifier an operator flips to
  disable the capability without a redeploy.
- LINT005 (flow fan-in exceeding declared downstream capacity,
  unconditional): a node with a declared `capacity` whose TOTAL inbound
  flow rate (every flow, no caching exclusion) exceeds
  `service_rate * replicas_max` -- deliberately CACHING-AGNOSTIC (unlike
  LINT002): caching relieves REPEATED READS of the SAME node acting as a
  source of truth, but does nothing for a node that is itself a compute
  sink with no cache construct possible over it (a queue consumer, a
  balancer target). LINT005 is the jurisdiction-agnostic baseline
  ("if fan-in physically exceeds every declared replica's combined
  capacity, that is an overload regardless of caching"); LINT002 is a
  narrower, caching-escapable tightening for store-shaped nodes. A model
  can fail LINT002 and pass LINT005 (caching-covered, but the covered
  node itself is uncapacitated below its callers' declared rate) or vice
  versa (no cache, but replicas_max headroom absorbs the fan-in) -- the
  exact PII003/GDPR-RETENTION precedent (`_pii.py` module docstring).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._effects import _may_kind
from ._errors import StrataError
from ._models import BoundClaim, KernelModel, Metric, Node, Quantity, ScaleRate

_log = get_logger(__name__)

#: Node attr prefix for a declared kill-switch/feature-flag reference
#: (mirrors `_pii.py::_PII_PREFIX`'s `pii=<tag>` convention; authored via
#: the grammar's generic `attr flag=<id>;` node property, no new keyword).
_FLAG_PREFIX = "flag="

#: `may` capability KINDS this ticket treats as "risky enough to need a
#: live kill-switch" (T-0150's tier-1 classes: arbitrary code execution
#: and outbound network egress -- module docstring). Deliberately narrower
#: than `_threat.py`'s full sink taxonomy: LINT004 is an OPERATIONAL
#: (can-you-turn-it-off-live) concern, not a weakness-classification one.
# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
RISKY_CAPABILITY_KINDS: frozenset[str] = frozenset({"exec", "net"})

#: Flow attrs marking std.infra caching-layer traffic against a source of
#: truth (`_infra.py::_elaborate_cache`) -- excluded from LINT002's summed
#: client-demand load (module docstring).
_INFRA_LOAD_EXEMPT_ATTRS = frozenset({"fill", "invalidation"})


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:doc docs/guides/extending/design-lint-rules.md#design-lint-rules-lint001-005
class LintViolation(BaseModel):
    """One LINT001-005 finding: a rule id, the firing target (node/flow/
    scenario id), and a human detail. Mirrors `_pii.py::PiiViolation`'s
    shape so a caller merging every family's report treats LINT
    identically."""

    model_config = ConfigDict(frozen=True)

    rule: str  # LINT001 rate | LINT002 cache | LINT003 surge | LINT004 kill-switch
    # LINT005 fan-in
    target: str | None = None
    detail: str = ""


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
class LintReport(BaseModel):
    """Every LINT001-005 violation, in rule-then-target order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[LintViolation, ...] = ()


def node_flag_ids(node: Node) -> tuple[str, ...]:
    """Every kill-switch/feature-flag id `node` declares via `attr
    flag=<id>` (i.e. every `flag=<id>` attr, `_FLAG_PREFIX` convention)."""
    # frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
    return tuple(
        attr[len(_FLAG_PREFIX) :]
        for attr in node.attrs
        if attr.startswith(_FLAG_PREFIX)
    )


def _rate_base(quantity_owner: str, value: Quantity) -> Result[float, StrataError]:
    """A `Quantity`'s value converted to its base rate unit, failing closed
    (`StrataError.UnitMismatch`) if its dimension is not `"rate"` --
    shared by every rule below that sums or compares declared rates so a
    mis-dimensioned quantity (e.g. a `rate` field accidentally given a
    time unit) is refused rather than silently miscompared."""
    dimension = value.dimension()
    if dimension.is_err:
        return Err(dimension.danger_err)
    if dimension.danger_ok != "rate":
        _log.error(
            "lint: %s declares a non-rate quantity %s%s where a rate was expected",
            quantity_owner,
            value.value,
            value.unit,
        )
        return Err(StrataError.UnitMismatch)
    return value.base_value()


def _sum_flow_rates(flows: list) -> Result[float, StrataError]:
    """Sum a list of flows' rates in their base rate unit, shared by
    LINT002/LINT005's inbound-load summation (charter law 5: no
    duplication) -- fails closed on the first mis-dimensioned quantity."""
    total = 0.0
    for flow in flows:
        assert flow.rate is not None  # callers filter this
        base = _rate_base(flow.id, flow.rate)
        if base.is_err:
            return Err(base.danger_err)
        total += base.danger_ok
    return Ok(total)


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:enforces CHK-GATE-LINT001
def check_lint_rate_limit(
    model: KernelModel,
) -> Result[tuple[LintViolation, ...], StrataError]:
    """LINT001: every flow sourced from a `foreign`-trust node declares a
    `rate` -- `Flow.rate` IS the rate-limit declaration (module
    docstring), so an undeclared rate on an external-facing edge is a
    public/edge boundary with no throughput bound at all. No claim
    override (module docstring: a missing rate is a missing fact)."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[LintViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for flow in sorted(model.flows, key=lambda f: f.id):
        src = nodes_by_id.get(flow.src)
        if src is None or src.trust != "foreign":
            continue
        if flow.rate is not None:
            continue
        _log.warning(
            "lint: LINT001 flow %s from foreign node %s has no declared rate",
            flow.id,
            flow.src,
        )
        violations.append(
            LintViolation(
                rule="LINT001",
                target=flow.id,
                detail=f"flow {flow.id} accepts external input from {src.id} "
                "(foreign trust) with no declared rate -- an edge boundary "
                "needs a declared rate limit",
            )
        )
    return Ok(tuple(violations))


def _cache_covers(model: KernelModel, node_id: str) -> bool:
    """Whether a `cache X of node_id` construct is declared over
    `node_id` -- detected as a `fill`-attr flow SOURCED from `node_id`
    (`_infra.py::_elaborate_cache`'s fill-flow convention), never a
    second cache-detection heuristic."""
    return any(f.src == node_id and "fill" in f.attrs for f in model.flows)


def _check_lint002_node(
    model: KernelModel, node: Node
) -> Result[LintViolation | None, StrataError]:
    """LINT002 check for one capacitated node: `None` if it does not
    violate, else the `LintViolation` -- factored out of
    `check_lint_cache_or_capacity` so that loop stays a thin dispatcher."""
    inbound = [
        f
        for f in model.flows
        if f.dst == node.id
        and f.rate is not None
        and not (set(f.attrs) & _INFRA_LOAD_EXEMPT_ATTRS)
    ]
    assert node.capacity is not None
    if not inbound:
        return Ok(None)
    total_r = _sum_flow_rates(inbound)
    if total_r.is_err:
        return Err(total_r.danger_err)
    total = total_r.danger_ok
    service = _rate_base(node.id, node.capacity.service_rate)
    if service.is_err:
        return Err(service.danger_err)
    if total <= service.danger_ok:
        return Ok(None)
    if _cache_covers(model, node.id):
        return Ok(None)
    return Ok(_lint002_violation(node, inbound, total, service.danger_ok))


def _lint002_violation(
    node: Node, inbound: list, total: float, service: float
) -> LintViolation:
    """Build the LINT002 `LintViolation` for a node whose inbound load
    exceeds its declared service rate with no cache -- split out of
    `_check_lint002_node` purely to keep that function's body short."""
    assert node.capacity is not None
    _log.warning(
        "lint: LINT002 node %s inbound rate %.4f exceeds service rate "
        "%.4f with no cache",
        node.id,
        total,
        service,
    )
    return LintViolation(
        rule="LINT002",
        target=node.id,
        detail=f"node {node.id} declared service rate "
        f"{node.capacity.service_rate.value}{node.capacity.service_rate.unit} "
        f"is exceeded by inbound flow(s) {[f.id for f in inbound]} with no "
        "cache/TTL declared over it",
    )


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:enforces CHK-GATE-LINT002
def check_lint_cache_or_capacity(
    model: KernelModel,
) -> Result[tuple[LintViolation, ...], StrataError]:
    """LINT002: a node with a declared `capacity.service_rate` whose
    non-infra inbound flows' combined rate exceeds that service rate, with
    no caching escape valve (`_cache_covers`) declared over it -- deny by
    default (module docstring)."""
    violations: list[LintViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        if node.capacity is None:
            continue
        result = _check_lint002_node(model, node)
        if result.is_err:
            return Err(result.danger_err)
        if result.danger_ok is not None:
            violations.append(result.danger_ok)
    return Ok(tuple(violations))


def _scenario_touched_nodes(model: KernelModel, flow_id: str) -> tuple[str, ...]:
    """The node ids touched by a `ScaleRate` rewrite on `flow_id`: the
    scaled flow's src and dst -- a surge on a flow is a surge on both its
    endpoints."""
    flow = next((f for f in model.flows if f.id == flow_id), None)
    if flow is None:
        return ()
    return (flow.src, flow.dst)


def _scenario_has_bound_claim(
    scenario, flow_id: str, node_ids: tuple[str, ...]
) -> bool:
    """Whether `scenario` nests a `BoundClaim` (RATE or UTILIZATION)
    targeting the scaled flow or either of its endpoints -- structural
    presence only (module docstring: asserted or assumed both count)."""
    for claim in scenario.claims:
        body = claim.body
        if not isinstance(body, BoundClaim):
            continue
        if body.metric not in (Metric.RATE, Metric.UTILIZATION):
            continue
        if body.target == flow_id or body.target in node_ids:
            return True
    return False


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:enforces CHK-GATE-LINT003
def check_lint_surge_capacity_bound(model: KernelModel) -> tuple[LintViolation, ...]:
    """LINT003: every `Scenario` with a `ScaleRate` rewrite nests a
    `BoundClaim` (RATE or UTILIZATION) targeting the scaled flow or one of
    its endpoints -- a surge scenario with nothing to re-check under the
    rewrite is a scenario that proves nothing (module docstring)."""
    violations: list[LintViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for scenario in sorted(model.scenarios, key=lambda s: s.id):
        for rewrite in scenario.rewrites:
            if not isinstance(rewrite, ScaleRate):
                continue
            node_ids = _scenario_touched_nodes(model, rewrite.flow_id)
            if _scenario_has_bound_claim(scenario, rewrite.flow_id, node_ids):
                continue
            _log.warning(
                "lint: LINT003 scenario %s scales flow %s with no nested "
                "capacity bound claim",
                scenario.id,
                rewrite.flow_id,
            )
            violations.append(
                LintViolation(
                    rule="LINT003",
                    target=scenario.id,
                    detail=f"scenario {scenario.id} scales flow {rewrite.flow_id} "
                    f"(factor {rewrite.factor}) with no nested bound(rate|"
                    f"utilization) claim over {rewrite.flow_id!r} or its endpoints "
                    f"{node_ids}",
                )
            )
    return tuple(violations)


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:enforces CHK-GATE-LINT004
def check_lint_kill_switch(model: KernelModel) -> tuple[LintViolation, ...]:
    """LINT004: every node holding a risky (`RISKY_CAPABILITY_KINDS`) `may`
    capability declares a `flag=<id>` kill-switch attr (module
    docstring)."""
    violations: list[LintViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        kinds = sorted({_may_kind(atom) for atom in node.may} & RISKY_CAPABILITY_KINDS)
        if not kinds:
            continue
        if node_flag_ids(node):
            continue
        _log.warning(
            "lint: LINT004 node %s holds risky capability kind(s) %s with no "
            "declared kill-switch",
            node.id,
            kinds,
        )
        violations.append(
            LintViolation(
                rule="LINT004",
                target=node.id,
                detail=f"node {node.id} holds risky capability kind(s) {kinds} "
                "with no declared attr flag=<id> kill-switch -- declare "
                "`attr flag=<id>;` naming a real kill-switch, or `waive "
                '"LINT004" reason "..." ticket "T-...";` until one lands',
            )
        )
    return tuple(violations)


def _check_lint005_node(
    node: Node, model: KernelModel
) -> Result[LintViolation | None, StrataError]:
    """LINT005 check for one capacitated node: `None` if it does not
    violate, else the `LintViolation` -- factored out of
    `check_lint_fanin_capacity` so that loop stays a thin dispatcher."""
    inbound = [f for f in model.flows if f.dst == node.id and f.rate is not None]
    assert node.capacity is not None
    if not inbound:
        return Ok(None)
    total_r = _sum_flow_rates(inbound)
    if total_r.is_err:
        return Err(total_r.danger_err)
    total = total_r.danger_ok
    service = _rate_base(node.id, node.capacity.service_rate)
    if service.is_err:
        return Err(service.danger_err)
    headroom = service.danger_ok * node.capacity.replicas_max
    if total <= headroom:
        return Ok(None)
    return Ok(_lint005_violation(node, total, headroom))


def _lint005_violation(node: Node, total: float, headroom: float) -> LintViolation:
    """Build the LINT005 `LintViolation` for a node whose fan-in exceeds
    its capacity headroom -- split out of `_check_lint005_node` purely to
    keep that function's body short."""
    assert node.capacity is not None
    _log.warning(
        "lint: LINT005 node %s fan-in rate %.4f exceeds capacity headroom %.4f",
        node.id,
        total,
        headroom,
    )
    return LintViolation(
        rule="LINT005",
        target=node.id,
        detail=f"node {node.id} total inbound rate {total} exceeds declared "
        f"capacity headroom {headroom} ({node.capacity.service_rate.value}"
        f"{node.capacity.service_rate.unit} x {node.capacity.replicas_max} "
        "replicas)",
    )


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
# frob:enforces CHK-GATE-LINT005
def check_lint_fanin_capacity(
    model: KernelModel,
) -> Result[tuple[LintViolation, ...], StrataError]:
    """LINT005: a node with a declared `capacity` whose TOTAL inbound flow
    rate (unconditional -- no caching exclusion, module docstring)
    exceeds `service_rate * replicas_max`."""
    violations: list[LintViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        if node.capacity is None:
            continue
        result = _check_lint005_node(node, model)
        if result.is_err:
            return Err(result.danger_err)
        if result.danger_ok is not None:
            violations.append(result.danger_ok)
    return Ok(tuple(violations))


# frob:doc docs/strata/threat.md#operational-design-lints-stdlint-t-0155
def evaluate_lint(model: KernelModel) -> Result[LintReport, StrataError]:
    """The strata-level operational-lint entrypoint: LINT001-005 over
    `model` (module docstring). Kept gate-agnostic (no `src/frob/gates`
    import), mirroring `_pii.py::evaluate_pii` / `_compliance.py::
    evaluate_compliance`."""
    rate = check_lint_rate_limit(model)
    if rate.is_err:
        return Err(rate.danger_err)
    cache = check_lint_cache_or_capacity(model)
    if cache.is_err:
        return Err(cache.danger_err)
    fanin = check_lint_fanin_capacity(model)
    if fanin.is_err:
        return Err(fanin.danger_err)

    all_violations = (
        *rate.danger_ok,
        *cache.danger_ok,
        *check_lint_surge_capacity_bound(model),
        *check_lint_kill_switch(model),
        *fanin.danger_ok,
    )
    _log.info(
        "lint: evaluated %d node(s)/%d flow(s)/%d scenario(s) -> %d violation(s)",
        len(model.nodes),
        len(model.flows),
        len(model.scenarios),
        len(all_violations),
    )
    return Ok(LintReport(violations=all_violations))


__all__ = [
    "RISKY_CAPABILITY_KINDS",
    "LintReport",
    "LintViolation",
    "check_lint_cache_or_capacity",
    "check_lint_fanin_capacity",
    "check_lint_kill_switch",
    "check_lint_rate_limit",
    "check_lint_surge_capacity_bound",
    "evaluate_lint",
    "node_flag_ids",
]
