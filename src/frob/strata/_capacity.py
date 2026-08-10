"""T-1927: population-projected capacity evaluator for `frob sys capacity
[--population N]` (docs/strata/roadmap.md "CLI surface (target)").

Filed as a T-1480 residue rather than folded into that ticket: no
existing evaluator projects a `Capacity` threshold against a POPULATION
parameter at all (`_starvation.py`'s REL380/REL381 utilization checks
compare `FactBase.aggregate_demand` as DECLARED, never scaled) -- this is
new modeling work, not a CLI-glue gap over an already-shipped primitive.

Scope cut, disclosed rather than silently dropped (T-2016, filed by this
ticket): `--at DATE` from the roadmap's target signature is NOT
implemented here. Projecting to a DATE needs a growth-rate declaration on
`Node.users`/`rate` (docs/strata/kernel.md#demand-declarations-t-0702)
that the surface grammar does not have yet -- inventing one is a language
change, out of this ticket's "evaluator over the existing model" scope.
`--population N` needs no new grammar: it scales the model's OWN already-
declared `users` population linearly, which is sound with today's data.

T-2016 designed (not yet implemented) the missing grammar --
docs/strata/kernel.md#growth-rate-declarations-t-2016 -- including why
this module's own single-scalar `scale` cannot simply be reused for a
per-node growth rate (each demand-declaring node's synthetic seed rate
needs its OWN growth projection applied BEFORE `aggregate_demand`'s BFS
summation, not a scalar applied after) and one open decision (a
model-level `as_of DATE` vs. a CLI-only `--since DATE`) an implementer
needs from the ticket owner before starting.
"""

from __future__ import annotations

from dataclasses import dataclass

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import FactBase
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: `frob sys audit`-shaped rule id this module's finding uses, mirroring
#: `_starvation.py::REL_SERIALIZATION_UTILIZATION`'s own naming
#: convention (a two-letter-family + 3-digit id) -- SYS2xx is already the
#: resource-contention family (`_starvation.py`'s own module docstring
#: references SYS20x elsewhere in this package), so CAP (capacity) is a
#: fresh, non-colliding family for this ticket's own finding kind.
# frob:doc docs/strata/reliability.md#population-projected-capacity-t-1927
CAPACITY_PROJECTED_OVER_THRESHOLD = "CAP001"


# frob:doc docs/strata/reliability.md#population-projected-capacity-t-1927
@dataclass(frozen=True)
class CapacityViolation:
    """One node whose PROJECTED demand exceeds its declared `Capacity`
    (`service_rate * replicas_max`, the ordinary throughput ceiling --
    unlike REL380's deliberate singleton-only comparison, this evaluator
    IS scaling by replica count, since it answers "how many replicas do
    we need", not "is this exclusive serialization point already
    overloaded")."""

    node: str
    projected_demand: float
    capacity: float
    detail: str = ""


# frob:doc docs/strata/reliability.md#population-projected-capacity-t-1927
@dataclass(frozen=True)
class CapacityReport:
    """The result of one `project_capacity` run: every `CapacityViolation`
    found, plus the `scale_factor` actually applied (1.0 for an
    unscaled/current-population run) and the `baseline_population` the
    scale was computed against (`None` when no node in the model declares
    `users` at all -- distinguishable from a genuine zero, T-0702's own
    "missing demand is not zero demand" mandate applied here)."""

    violations: tuple[CapacityViolation, ...] = ()
    scale_factor: float = 1.0
    baseline_population: float | None = None


def _baseline_population(model: KernelModel) -> float | None:
    """The model's own declared population baseline: the sum of every
    node's `users` field that declares one, or `None` if no node declares
    `users` at all -- the denominator `--population N` scales against.
    `None` (not `0.0`) distinguishes "this model declares no population"
    from "this model declares a population of zero", mirroring
    `AggregateDemand.declared`'s own distinction (`_facts.py`)."""
    declared = tuple(n.users for n in model.nodes if n.users is not None)
    if not declared:
        return None
    return sum(declared)


def _node_capacity_per_second(node: Node) -> float | None:
    """A node's total (all-replicas) throughput ceiling:
    `service_rate.base_value() * replicas_max`, or `None` when the node
    declares no `Capacity` at all, or its `service_rate` unit is
    unresolvable (fails closed by omission -- a node with no comparable
    capacity is simply not checked, never treated as either infinite or
    zero capacity)."""
    if node.capacity is None:
        return None
    base = node.capacity.service_rate.base_value()
    if base.is_err:
        _log.warning(
            "capacity: node %s capacity.service_rate unresolvable (%s), "
            "skipping",
            node.id,
            base.danger_err,
        )
        return None
    return base.danger_ok * node.capacity.replicas_max


def _capacity_violation(
    node_id: str, projected_demand: float, capacity: float
) -> CapacityViolation:
    """CAP001 violation helper: a node's projected demand exceeds its
    declared total-replica capacity."""
    _log.warning(
        "capacity: CAP001 node %s projected demand=%s/s exceeds capacity=%s/s",
        node_id,
        projected_demand,
        capacity,
    )
    return CapacityViolation(
        node=node_id,
        projected_demand=projected_demand,
        capacity=capacity,
        detail=f"projected demand {projected_demand}/s exceeds declared "
        f"capacity {capacity}/s ({CAPACITY_PROJECTED_OVER_THRESHOLD})",
    )


# frob:doc docs/strata/reliability.md#population-projected-capacity-t-1927
# frob:ticket T-1927
def project_capacity(
    model: KernelModel, facts: FactBase, *, population: float | None = None
) -> Result[CapacityReport, StrataError]:
    """T-1927: the `frob sys capacity [--population N]` evaluator --
    every node declaring a `Capacity` (docs/strata/kernel.md
    #capacity-semantics) whose `FactBase.aggregate_demand` (T-0702's
    users/rate propagation closure), scaled to `population`, exceeds
    `service_rate * replicas_max` is a `CapacityViolation`.

    `population is None` runs unscaled (`scale_factor=1.0`, the model's
    OWN declared demand as-is -- "is today's declared model already over
    capacity"). A given `population` scales linearly against
    `_baseline_population(model)` (the model's own summed `users`
    declarations): `scale = population / baseline`. Returns
    `Err(StrataError.UnknownReference)` when `population` is given but
    the model declares NO baseline population to scale against -- fails
    closed rather than silently treating an unscalable projection as
    "no violations found" (deny-by-default, the same posture
    `check_catalog_completeness`'s unknown-view refusal takes for an
    unanswerable question, `_threat.py`).
    """
    scale = 1.0
    baseline = _baseline_population(model)
    if population is not None:
        if baseline is None or baseline <= 0:
            _log.error(
                "capacity: --population %s requested but model declares no "
                "baseline `users` population to scale against",
                population,
            )
            return Err(StrataError.UnknownReference)
        scale = population / baseline

    violations: list[CapacityViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        capacity = _node_capacity_per_second(node)
        if capacity is None:
            continue
        # `aggregate_demand`, not `demand`/`propagated_demand`: T-0702's
        # `users`/`rate` node declarations are the population source this
        # evaluator projects, and only `aggregate_demand` seeds from them
        # (`propagated_demand` alone only sums explicit `Flow.rate`
        # values, which a `users`-declaring model may never set).
        aggregate = facts.aggregate_demand(node.id)
        projected_demand = aggregate.value * scale
        if projected_demand > capacity:
            violations.append(
                _capacity_violation(node.id, projected_demand, capacity)
            )

    return Ok(
        CapacityReport(
            violations=tuple(violations),
            scale_factor=scale,
            baseline_population=baseline,
        )
    )


__all__ = [
    "CAPACITY_PROJECTED_OVER_THRESHOLD",
    "CapacityReport",
    "CapacityViolation",
    "project_capacity",
]
