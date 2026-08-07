"""REL25x reliability family: SPOF (single point of failure) detection --
an inbound-critical-flow node with `replicas_max=1`/no declared redundancy
(T-0645, child of the T-0331 systems-checks epic, docs/strata/
reliability.md), mirroring `_circuit_breaker.py`/`_fallback.py`'s REL2xx
structure (module docstring precedent: one rule module per obligation,
same `Report`/`Violation` pydantic pair, node-scoped single-instance
waiver carve-out, CLI wiring via `frob.app.sys_runner`).

Unlike every sibling REL2xx family in this ticket cluster (T-0640/T-0641/
T-0642/T-0643), REL25x is ONE RULE, not a missing/unproven PAIR: SPOF is a
STRUCTURAL fact readable straight off the kernel model
(`Capacity.replicas_max`/`Capacity.singleton`, already a typed field --
`_models.py::Capacity`, no new kernel field, charter law 1) rather than an
operator-declared obligation needing separate proof-against-code. There is
no "declared but unproven redundancy" to check; a node's replica count
either structurally is or is not a single point of failure this run.

  - REL250 SPOF: a node that is the `dst` of at least one inbound flow
    carrying the `critical` attr (T-0642's `CRITICAL_ATTR`, reused here
    for the flow-level analog -- a flow this system cannot tolerate
    losing), AND whose own capacity is a structural singleton
    (`node.capacity is None` -- no capacity declared at all, defaulting
    to `_models.py::Capacity`'s own `replicas_min`/`replicas_max`
    defaults of 1, which IS the "no declared redundancy" case this rule
    exists for -- or `node.capacity.singleton` is `True`, i.e.
    `replicas_max == 1` even when capacity IS declared), AND the node
    does not carry the `redundant` exemption attr (an explicit modeler
    assertion that real redundancy exists outside what `Capacity`
    expresses, e.g. active-passive failover to a node this grammar does
    not yet model). Deny-by-default with a reasoned waive channel
    (T-0174), same discipline every REL2xx obligation in this cluster
    uses.

`CRITICAL_ATTR` here marks a FLOW, not a node -- deliberately reusing
T-0642's exact string rather than inventing a second "this matters"
vocabulary word, but at a different grammar site (`Flow.attrs`, not
`Node.attrs`): a dependency can be `critical` (T-0642/T-0643's node-level
sense: this NODE is a critical dependency of the caller) while a flow INTO
some other node can separately be `critical` (this rule's sense: this
PATH is a critical inbound path the destination node cannot lose). Both
readings share one word because they express the same underlying idea
("this must not fail") at two different grammar sites the kernel already
distinguishes (`Node.attrs` vs `Flow.attrs`) -- not a naming collision, the
same bare-marker-reused-at-two-sites shape `_retry.py`'s module docstring
already discusses for why `_IDEMPOTENT_ATTR` stays a local copy rather
than a shared import when the REUSE is coincidental; here the reuse is
deliberate (both markers mean "must not fail", just at different grammar
sites), so the literal string is intentionally the SAME as T-0642's
`CRITICAL_ATTR` value, without importing it (importing would wrongly imply
these two attrs share validation/scope, when they are independent
declarations at independent grammar sites).

GRAMMAR-DATA CEILING, HONESTLY: `critical` (on a Flow) and `redundant` (on
a Node) are both bare presence-only attrs -- the same digit-led-literal
ceiling every other REL2xx marker in this family discloses. `replicas_max`
needs NO new ceiling disclosure at all: `Capacity.replicas_max` is already
a typed `int` field on the EXISTING `_models.py::Capacity` model (not a
bare attr), so this rule reads real structural data, not a presence-only
proxy for it -- REL250 is the one REL2xx rule in this ticket cluster that
does not need a proof-against-code companion, because there is nothing to
prove beyond the declared capacity itself.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._models import KernelModel, Node
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL250 SPOF: a node receiving at least one
#: inbound `critical` flow with `replicas_max=1`/no declared redundancy.
# frob:doc docs/strata/reliability.md#rel25x-spof-detection-t-0645
REL_SPOF = "REL250"

#: Every REL25x rule id this module can emit -- this module's own, narrow
#: family for `_apply_spof_waivers`' `in_scope` (the same "never a shared
#: superset" discipline `_reliability.py`'s module docstring documents the
#: real regression for). A one-element frozenset today (REL25x is a single
#: rule, module docstring), kept as a set (not a bare constant comparison)
#: so a future REL25x sibling rule slots into `_apply_spof_waivers`
#: without a call-site change.
# frob:doc docs/strata/reliability.md#rel25x-spof-detection-t-0645
SPOF_RULES: frozenset[str] = frozenset({REL_SPOF})

#: Flow attr marking an inbound flow this system cannot tolerate losing --
#: the SAME string as `_circuit_breaker.py::CRITICAL_ATTR`, deliberately
#: not imported from there (module docstring: same word, two independent
#: grammar sites -- Node.attrs there, Flow.attrs here).
_CRITICAL_FLOW_ATTR = "critical"

#: Node attr exempting a structural-singleton node from REL250 -- an
#: explicit modeler assertion that real redundancy exists outside what
#: `Capacity` expresses (e.g. active-passive failover to an unmodeled
#: node).
_REDUNDANT_ATTR = "redundant"


# frob:doc docs/strata/reliability.md#rel25x-spof-detection-t-0645
class SpofViolation(BaseModel):
    """One REL250 finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (a node either
    is or is not this run's SPOF; module docstring), the same bare-rule
    waiver carve-out REL210/REL211/REL230/REL231/REL240/REL241 use.
    Mirrors `_fallback.py::FallbackViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel25x-spof-detection-t-0645
class SpofReport(BaseModel):
    """Every UNWAIVED REL250 finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_fallback.py::FallbackReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SpofViolation, ...] = ()
    waived: tuple[SpofViolation, ...] = ()


def _nodes_by_id(model: KernelModel) -> dict[str, Node]:
    """Node id -> `Node`, once -- the per-node lookup REL250 needs rather
    than a linear `model.nodes` scan per critical-inbound target."""
    return {node.id: node for node in model.nodes}


def _is_structural_singleton(node: Node) -> bool:
    """Whether `node`'s declared capacity is a structural singleton: no
    `Capacity` declared at all (defaults to `replicas_max=1`, the "no
    declared redundancy" case this rule exists for), or a declared
    `Capacity` whose `replicas_max == 1` (`Capacity.singleton`)."""
    if node.capacity is None:
        return True
    return node.capacity.singleton


def _is_redundant(node: Node) -> bool:
    """Whether `node` carries the `redundant` exemption attr."""
    return _REDUNDANT_ATTR in node.attrs


def _critical_inbound_targets(model: KernelModel) -> set[str]:
    """Every node id that is the `dst` of at least one `critical` flow."""
    return {flow.dst for flow in model.flows if _CRITICAL_FLOW_ATTR in flow.attrs}


def _spof_violations(model: KernelModel) -> list[SpofViolation]:
    """REL250: every node receiving a `critical` inbound flow whose own
    capacity is a structural singleton and who does not declare
    `redundant`. A `critical` flow's dst that names no real node in
    `model.nodes` is skipped -- not this rule's job to flag a dangling
    flow reference (a different gate's concern)."""
    violations: list[SpofViolation] = []
    node_by_id = _nodes_by_id(model)
    for node_id in sorted(_critical_inbound_targets(model)):
        node = node_by_id.get(node_id)
        if node is None:
            continue
        if not _is_structural_singleton(node) or _is_redundant(node):
            continue
        _log.warning(
            "spof: REL250 node %s receives critical inbound flow(s) with "
            "no redundancy (replicas_max=1/undeclared capacity)",
            node_id,
        )
        violations.append(
            SpofViolation(
                rule=REL_SPOF,
                node=node_id,
                detail=(
                    f"node {node_id} receives a critical inbound flow with "
                    "no redundancy (replicas_max=1 or no declared capacity, "
                    "no `redundant` exemption) -- single point of failure"
                ),
            )
        )
    return violations


def _apply_spof_waivers(model: KernelModel, violations: list[SpofViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_fallback.py::_apply_fallback_waivers`'s pattern reused for the
    REL25x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SPOF_RULES,
    )


# frob:doc docs/strata/reliability.md#rel25x-spof-detection-t-0645
# frob:ticket T-0645
# frob:enforces CHK-GATE-REL250
# frob:tests tests/unit/strata/test_spof.py::TestSpof.test_singleton_node_with_critical_inbound_fires  # noqa: E501
def check_spof(model: KernelModel) -> SpofReport:
    """The REL25x SPOF-detection entrypoint (T-0645): REL250 across every
    node in `model` receiving a `critical` inbound flow, waivers already
    applied. Unlike every sibling REL2xx entrypoint in this ticket cluster
    this takes no `root`/`bind_code` call -- REL250 is a pure structural
    read of the kernel model (module docstring), so it cannot `Err` the
    way a proof-against-code entrypoint can; the return type stays a bare
    `SpofReport`, not a `Result`, honestly reflecting that."""
    violations = _spof_violations(model)
    applied = _apply_spof_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        SpofViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            sub_target=stale_waiver.rule,
            detail=(
                f"waive {stale_waiver.rule!r} on node {stale_waiver.node} "
                f"reason={stale_waiver.reason!r} is stale -- no matching "
                f"finding fired this run"
            ),
        )
        for stale_waiver in applied.stale
    )
    _log.info(
        "spof: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return SpofReport(violations=tuple(applied.kept) + stale, waived=waived)


__all__ = [
    "REL_SPOF",
    "SPOF_RULES",
    "SpofReport",
    "SpofViolation",
    "check_spof",
]
