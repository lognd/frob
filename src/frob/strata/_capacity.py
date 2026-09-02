"""T-1927/T-2016: population- and growth-rate-projected capacity evaluator
for `frob sys capacity [--population N] [--since DATE --at DATE]`
(docs/strata/roadmap.md "CLI surface (target)").

Filed as a T-1480 residue rather than folded into that ticket: no
existing evaluator projects a `Capacity` threshold against a POPULATION
parameter at all (`_starvation.py`'s REL380/REL381 utilization checks
compare `FactBase.aggregate_demand` as DECLARED, never scaled) -- this is
new modeling work, not a CLI-glue gap over an already-shipped primitive.
`--population N` needs no new grammar: it scales the model's OWN already-
declared `users` population linearly, which is sound with today's data.

T-2016 (docs/strata/kernel.md#growth-rate-declarations-t-2016) implements
`--since DATE --at DATE`: unlike `--population`'s single post-hoc scalar,
a `growth`-declaring node's seed is scaled by ITS OWN compound growth
factor BEFORE `FactBase.aggregate_demand`'s BFS summation runs
(`elapsed_seconds` threaded through to `aggregate_demand` itself, per
that function's own UNMISSABLE design note) -- this module only computes
the elapsed time between `--since`/`--at` and forwards it, since
`aggregate_demand` already consumes growth as a per-node input. The
CLI-only `--since`/`--at` pair (no model-level `as_of` construct) was the
ticket-owner's decided anchor-date design (kernel.md's own "The anchor
date -- DECIDED" section) -- a model without `growth` behaves exactly as
before either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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
    #: T-2016: the elapsed time (in seconds) `--since DATE --at DATE`
    #: projected growth over, or `None` for an unprojected run -- same
    #: "distinguishable, not just absent" transparency `scale_factor`
    #: already gives `--population`.
    elapsed_seconds: float | None = None


def _elapsed_seconds(since: datetime, at: datetime) -> float:
    """`(at - since)` in seconds -- may be negative (a `--at` before
    `--since` is not specially rejected, kernel.md's own "No retroactive/
    negative-time projection guardrail" note: the compound growth formula
    already produces a coherent, smaller-not-negative answer)."""
    return (at - since).total_seconds()


def _resolve_population_scale(
    model: KernelModel, population: float | None
) -> Result[tuple[float, float | None], StrataError]:
    """`project_capacity`'s `--population` half: returns `(scale,
    baseline)`, or `Err(StrataError.UnknownReference)` when `population`
    is given but the model declares no baseline `users` population to
    scale against -- split out of `project_capacity` itself to keep that
    function under ARCH001's complexity threshold (T-2016 added the
    since/at half alongside it). Private helper; the doc anchor lives on
    the public caller `project_capacity` (see docs/strata/reliability.md
    #population-projected-capacity-t-1927)."""
    baseline = _baseline_population(model)
    if population is None:
        return Ok((1.0, baseline))
    if baseline is None or baseline <= 0:
        _log.error(
            "capacity: --population %s requested but model declares no "
            "baseline `users` population to scale against",
            population,
        )
        return Err(StrataError.UnknownReference)
    return Ok((population / baseline, baseline))


def _resolve_elapsed_seconds(
    since: datetime | None, at: datetime | None
) -> Result[float | None, StrataError]:
    """`project_capacity`'s T-2016 `--since`/`--at` half: `None` when
    neither is given (ungrown, byte-for-byte pre-T-2016 behavior),
    elapsed seconds when both are given, or `Err(StrataError.
    UnknownReference)` when only one is given -- an ambiguous request is
    refused, never silently defaulted. Private helper; the doc anchor
    lives on the public caller `project_capacity` (see docs/strata/
    kernel.md#growth-rate-declarations-t-2016)."""
    if (since is None) != (at is None):
        _log.error(
            "capacity: --since and --at must be given together (since=%s, at=%s)",
            since,
            at,
        )
        return Err(StrataError.UnknownReference)
    if since is None or at is None:
        return Ok(None)
    return Ok(_elapsed_seconds(since, at))


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
            "capacity: node %s capacity.service_rate unresolvable (%s), skipping",
            node.id,
            base.danger_err,
        )
        return None
    return base.danger_ok * node.capacity.replicas_max


# frob:enforces CHK-GATE-CAP001
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
# frob:doc docs/strata/kernel.md#growth-rate-declarations-t-2016
# frob:ticket T-1927
def project_capacity(
    model: KernelModel,
    facts: FactBase,
    *,
    population: float | None = None,
    since: datetime | None = None,
    at: datetime | None = None,
) -> Result[CapacityReport, StrataError]:
    """T-1927/T-2016: the `frob sys capacity [--population N] [--since
    DATE --at DATE]` evaluator -- every node declaring a `Capacity`
    (docs/strata/kernel.md#capacity-semantics) whose `FactBase.
    aggregate_demand` (T-0702's users/rate propagation closure), scaled
    to `population` and/or projected to `at`, exceeds `service_rate *
    replicas_max` is a `CapacityViolation`.

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

    `at` (T-2016) requires `since` -- the CLI-only anchor-date pair
    kernel.md's own "The anchor date -- DECIDED" section settled on, no
    model-level `as_of` construct. Both `None` (the default) runs
    ungrown, `elapsed_seconds=None`, byte-for-byte the pre-T-2016
    behavior. `at` given without `since` (or vice versa) is
    `Err(StrataError.UnknownReference)`, the same fails-closed posture
    `population`'s own unscalable-baseline case takes just above --
    an ambiguous request is refused, never silently defaulted. `--at`
    and `--population` compose: growth projects each node's OWN seed
    first (inside `aggregate_demand`), then `population`'s scalar applies
    to the already-grown aggregate, same order the linear scale already
    ran in before T-2016.
    """
    scale_result = _resolve_population_scale(model, population)
    if scale_result.is_err:
        return Err(scale_result.danger_err)
    scale, baseline = scale_result.danger_ok

    elapsed_result = _resolve_elapsed_seconds(since, at)
    if elapsed_result.is_err:
        return Err(elapsed_result.danger_err)
    elapsed_seconds = elapsed_result.danger_ok

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
        aggregate = facts.aggregate_demand(node.id, elapsed_seconds=elapsed_seconds)
        projected_demand = aggregate.value * scale
        if projected_demand > capacity:
            violations.append(_capacity_violation(node.id, projected_demand, capacity))

    return Ok(
        CapacityReport(
            violations=tuple(violations),
            scale_factor=scale,
            baseline_population=baseline,
            elapsed_seconds=elapsed_seconds,
        )
    )


__all__ = [
    "CAPACITY_PROJECTED_OVER_THRESHOLD",
    "CapacityReport",
    "CapacityViolation",
    "project_capacity",
]
