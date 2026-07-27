"""REL38x reliability family: STARVATION/THROUGHPUT obligations at every
serialization point the T-0700 access-mode/resource grammar and T-0702
demand-propagation grammar can now jointly express (T-0703, child of the
T-0331 systems-checks epic, docs/strata/reliability.md). Mirrors
`_spof.py`/`_shared_state.py`'s structural-fact shape (module docstring
precedent: reads real typed model data -- `Capacity.service_rate`,
`FactBase.aggregate_demand` -- rather than a bare presence marker needing
a proof-against-code companion) combined with `_reliability.py`'s deny-
by-default population scan, one rule module per obligation.

USER MANDATE (2026-07-22, the 500k-users-vs-exclusive-write-lock case):
THREE independent obligation families over the T-0700 `access "R" mode M`
grammar plus T-0702's `FactBase.aggregate_demand`:

  (1) SERIALIZATION-POINT UTILIZATION (REL380 over-threshold, REL381
      demand-undeclared): every node that IS an effective-concurrency-1
      serialization point for some resource -- it declares `access
      "R" mode M` with M one of `write`/`append`/`exclusive`/`alpha`
      (write-like, or an alpha-gated upgrade path -- module docstring
      of `_access.py` establishes the same closed vocabulary), OR it is
      named `arbitrated_by` for some `resource` block (a single arbiter
      serializes EVERY accessor of that resource, regardless of the
      arbiter's own declared mode, if any) -- compares `FactBase.
      aggregate_demand` reaching that node against its `Capacity.
      service_rate` (ONE replica's worth: exclusivity collapses
      effective concurrency to 1 no matter how many replicas
      `Capacity.replicas_max` declares, so this rule deliberately does
      NOT multiply by `replicas_max` the way an ordinary throughput
      claim would -- REL380's whole point is that scaling replicas does
      not scale a serialization point). Undeclared demand fails closed
      (REL381) rather than silently skipping the check just because the
      arithmetic cannot be filled in -- the acceptance criterion's own
      framing ("the check cannot be silently skipped"). A DECLARED
      capacity is compared as-is; an UNDECLARED capacity falls back to
      `_DEFAULT_HOLDING_TIME_SECONDS` (a conservative default holding
      time -- see the GRAMMAR-DATA CEILING section below), never treated
      as infinite/unbounded capacity (that would be an allow-by-default
      guess this obligation exists specifically to refuse).
  (2) WRITER STARVATION (REL382, advisory): a resource with >=1 `read`
      accessor and >=1 write-like accessor (`write`/`append`/
      `exclusive`), but NO `alpha` accessor declared for that resource --
      the T-0700 module docstring's own "alpha sits between read and
      write ... prevents perpetual reader preemption" framing means an
      absent alpha declaration on a read-heavy resource is exactly the
      starvation risk T-0700's grammar was designed to let a modeler
      discharge. Fires regardless of utilization (module docstring's
      "even at low utilization" framing) and regardless of whether the
      resource declares an arbiter -- an arbiter changes WHO waits, not
      WHETHER the read-preferring discipline can starve a writer.
  (3) UNBOUNDED WAIT (REL383): a node accessing a CONTENDED resource (2+
      total accessors of the same resource id -- genuine contention, not
      just a lone accessor) in a write-like or alpha mode, with no
      `timeout` attr declared on the accessing node itself. This is the
      T-0640 TIMEOUT family's own vocabulary (`_reliability.py::
      _TIMEOUT_ATTR`) reapplied at a NEW population this module owns (a
      contended-resource accessor, not a `Flow`) -- "joins the T-0640
      timeout obligation family" (ticket body) in spirit and vocabulary,
      not by touching `_reliability.py` itself (this ticket's scope is
      `src/frob/strata/**`/`tests/unit/strata/**` only, the same
      "one rule module per obligation, no shared-file edit" discipline
      T-0700's own module docstring establishes for SYS204 alongside
      SYS200-203).

COORDINATION, DISCLOSED: T-0645 (SPOF, `_spof.py`) already flags a
structural singleton receiving a `critical` inbound flow; a saturated
single arbiter (REL380 firing on an `arbitrated_by` node) is the
QUANTITATIVE version of the same underlying hazard (T-0645 checks
"can it fail", REL380 checks "is it already overloaded") -- deliberately
NOT merged into one rule, since they answer different questions from
different declarations (`critical` Flow attr vs `access`/`resource`
declarations) and a resource can be a REL380 finding with no `critical`
inbound flow at all (e.g. an internal contended cache). T-0646
(BACKPRESSURE, `_backpressure.py`) asks "is intake at this queue/consumer
bounded at all"; REL380 asks "does the numbers here already exceed
capacity" -- a queue can be REL260-clean (bounded intake declared) and
still REL380-dirty (the declared bound is arithmetically too small for
the demand reaching it), so both obligations coexist on the same node
without collapsing into each other.

GRAMMAR-DATA CEILING, HONESTLY: `_access.py`'s `access "R" mode M`
and `_facts.py`'s `users NUMBER` / `rate NUMBER UNIT` are the only
numeric surfaces this module reads; no `strata-core` change is made or
needed (this ticket's scope, same as T-0645/T-0646/T-0700/T-0702's).
There is deliberately NO "holding time" grammar clause -- `Capacity.
service_rate` (a `Quantity` already expressed as a rate, i.e. 1/time) IS
the holding-time hint in disguise for a DECLARED capacity (a service
rate of 100/s already encodes "each unit of work holds the serialization
point for ~10ms"). For a node with NO declared `Capacity` at all,
`_DEFAULT_HOLDING_TIME_SECONDS` (10ms, `_DEFAULT_CAPACITY_PER_SECOND` =
its reciprocal) stands in as the "default holding time" the acceptance
criterion's own wording names -- a deliberately conservative (SMALL)
default capacity, so an undeclared-capacity serialization point fails
toward "this cannot possibly keep up" rather than toward silently
assuming infinite throughput (charter law 2, deny-by-default). This
default is documented, not tunable per-model (no grammar clause reads it
back) -- a real capacity declaration always overrides it.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose mirroring \
# _spof.py/_ssot.py's own identical waiver for the identical reason (module \
# docstring precedent, T-0703), not a separate cross-module contract"

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._access import AccessMode, node_access_declarations
from ._ast import Module, ResourceDecl
from ._facts import FactBase
from ._models import KernelModel, Node
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL380 serialization-point utilization
#: over threshold: aggregate demand reaching an effective-concurrency-1
#: point exceeds its (declared or defaulted) capacity, with the
#: arithmetic shown in the finding detail.
# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
REL_SERIALIZATION_UTILIZATION = "REL380"

#: `frob sys audit` rule id for REL381 serialization-point demand
#: undeclared: an effective-concurrency-1 point whose aggregate inbound
#: demand cannot be computed at all (no `users`/`rate` declaration
#: reaches it) -- fail-closed, the check is never silently skipped.
# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
REL_SERIALIZATION_DEMAND_UNDECLARED = "REL381"

#: `frob sys audit` rule id for REL382 writer starvation advisory: a
#: read-heavy resource with a write-like accessor and no `alpha` accessor
#: declared -- readers can perpetually preempt the writer.
# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
REL_WRITER_STARVATION = "REL382"

#: `frob sys audit` rule id for REL383 unbounded wait: a node acquiring a
#: contended resource in a write-like/alpha mode with no declared
#: `timeout` on the acquiring node itself.
# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
REL_UNBOUNDED_WAIT = "REL383"

#: Every REL38x rule id this module can emit -- this module's own,
#: narrow family for `_apply_starvation_waivers`'s `in_scope` (the "never
#: a shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
STARVATION_RULES: frozenset[str] = frozenset(
    {
        REL_SERIALIZATION_UTILIZATION,
        REL_SERIALIZATION_DEMAND_UNDECLARED,
        REL_WRITER_STARVATION,
        REL_UNBOUNDED_WAIT,
    }
)

#: Access modes that collapse effective concurrency to 1 at the
#: accessing node itself (module docstring family (1)): a write-like
#: mode conflicts with anything (`_access.py::mode_conflict`), and
#: `alpha` gates a single future writer -- both make the accessing node
#: a serialization point for the resource it names.
_SERIALIZATION_MODES: frozenset[AccessMode] = frozenset(
    {AccessMode.WRITE, AccessMode.APPEND, AccessMode.EXCLUSIVE, AccessMode.ALPHA}
)

#: Write-like modes for REL382's writer-starvation population (module
#: docstring family (2)) -- deliberately EXCLUDES `alpha`: an `alpha`
#: accessor is the very discharge REL382 checks for, not itself part of
#: the "write-like accessor at risk of starving" population.
_WRITE_LIKE_MODES: frozenset[AccessMode] = frozenset(
    {AccessMode.WRITE, AccessMode.APPEND, AccessMode.EXCLUSIVE}
)

#: Node attr declaring an acquisition-side timeout obligation discharged
#: for REL383 -- the SAME string as `_reliability.py::_TIMEOUT_ATTR`,
#: deliberately not imported from there (module docstring family (3):
#: same vocabulary word, independent grammar site -- a Flow attr there,
#: a Node attr here -- the same "reuse is deliberate, import would wrongly
#: imply shared validation/scope" precedent `_spof.py`'s `_CRITICAL_FLOW_
#: ATTR` documents for `CRITICAL_ATTR`).
_TIMEOUT_ATTR = "timeout"

#: Conservative default holding time (seconds) assumed for a
#: serialization-point node with no declared `Capacity` (module
#: docstring's GRAMMAR-DATA CEILING section) -- 10ms, small enough that
#: any non-trivial declared demand exceeds the resulting default
#: capacity, per charter law 2 (deny-by-default: an undeclared capacity
#: must never read as "infinite").
_DEFAULT_HOLDING_TIME_SECONDS = 0.01

#: The default capacity (units/second) implied by
#: `_DEFAULT_HOLDING_TIME_SECONDS` -- `1 / holding_time`, the M/M/1
#: identity `_claims.py::_node_utilization` already uses (rate = 1 /
#: mean service time) applied as this module's own fallback ceiling.
_DEFAULT_CAPACITY_PER_SECOND = 1.0 / _DEFAULT_HOLDING_TIME_SECONDS


# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
class StarvationViolation(BaseModel):
    """One REL38x finding: rule id, the reporting node, a human-readable
    detail (REL380/REL381 embed the actual arithmetic per the acceptance
    criterion, "showing the arithmetic ... not a vibe"), and
    `sub_target` set to the resource id (module docstring: a node may
    access more than one resource, so REL38x joins `_waive.py::
    MULTI_INSTANCE_WAIVER_FAMILIES`, the same `RULE:SUBTARGET` discipline
    REL200/REL201 already establish for a node originating several
    flows)."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    resource: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
class StarvationReport(BaseModel):
    """Every UNWAIVED REL38x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_spof.py::SpofReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[StarvationViolation, ...] = ()
    waived: tuple[StarvationViolation, ...] = ()


def _resource_arbiters(module: Module) -> dict[str, ResourceDecl]:
    """Every declared `resource` statement, keyed by id -- mirrors
    `_access.py::_resource_arbiters` exactly (local copy, module
    docstring: independent grammar-adjacent modules keep their own copy
    rather than importing a sibling module's private helper)."""
    return {resource.id: resource for resource in module.resources}


def _resource_accessors(
    model: KernelModel,
) -> dict[str, list[tuple[str, AccessMode]]]:
    """Every (node id, mode) pair declaring `access` to each resource id,
    across every node in `model` -- mirrors `_access.py::
    _resource_accessors` exactly (same local-copy rationale)."""
    accessors: dict[str, list[tuple[str, AccessMode]]] = defaultdict(list)
    for node in model.nodes:
        for declaration in node_access_declarations(node):
            accessors[declaration.resource].append((node.id, declaration.mode))
    return accessors


def _serialization_points(model: KernelModel, module: Module) -> list[tuple[str, str]]:
    """Every (node id, resource id) pair that is an effective-
    concurrency-1 serialization point (module docstring family (1)):
    each write-like/alpha accessor of a resource, PLUS the resource's own
    declared `arbitrated_by` node (a single arbiter serializes every
    accessor of the resource it arbitrates, regardless of its own access
    mode, or even if it declares no `access` clause of its own at all).
    Deduplicated (a node named both an accessor AND the arbiter of the
    same resource reports once)."""
    accessors = _resource_accessors(model)
    arbiters = _resource_arbiters(module)
    points: set[tuple[str, str]] = set()
    for resource_id, pairs in accessors.items():
        for node_id, mode in pairs:
            if mode in _SERIALIZATION_MODES:
                points.add((node_id, resource_id))
    for resource_id, arbiter in arbiters.items():
        if arbiter.arbitrated_by is not None:
            points.add((arbiter.arbitrated_by, resource_id))
    return sorted(points)


def _capacity_per_second(node: Node) -> tuple[float, bool]:
    """`(capacity, is_declared)` for `node`'s single-replica service rate
    -- `Capacity.service_rate.base_value()` when declared and resolvable
    (module docstring: deliberately NOT multiplied by `replicas_max`,
    since exclusivity collapses effective concurrency to 1 no matter how
    many replicas exist), else `_DEFAULT_CAPACITY_PER_SECOND` (module
    docstring's conservative default-holding-time fallback)."""
    if node.capacity is not None:
        base = node.capacity.service_rate.base_value()
        if base.is_ok:
            return base.danger_ok, True
        _log.warning(
            "starvation: node %s capacity service_rate unresolvable (%s), "
            "falling back to default holding time",
            node.id,
            base.danger_err,
        )
    return _DEFAULT_CAPACITY_PER_SECOND, False


def _utilization_violations(
    model: KernelModel, module: Module, facts: FactBase
) -> list[StarvationViolation]:
    """REL380/REL381: for every serialization point (`_serialization_
    points`), fail closed with REL381 if aggregate demand reaching the
    node is undeclared; otherwise compare demand against
    `_capacity_per_second` and fire REL380 with the full arithmetic when
    demand exceeds capacity (utilization > 1.0, i.e. > 100%)."""
    violations: list[StarvationViolation] = []
    node_by_id = {node.id: node for node in model.nodes}
    for node_id, resource_id in _serialization_points(model, module):
        node = node_by_id.get(node_id)
        if node is None:
            continue
        demand = facts.aggregate_demand(node_id)
        if not demand.declared:
            _log.warning(
                "starvation: REL381 node %s resource %s is a serialization "
                "point with undeclared upstream demand -- fail closed",
                node_id,
                resource_id,
            )
            violations.append(
                StarvationViolation(
                    rule=REL_SERIALIZATION_DEMAND_UNDECLARED,
                    node=node_id,
                    resource=resource_id,
                    sub_target=resource_id,
                    detail=(
                        f"node {node_id!r} is an effective-concurrency-1 "
                        f"serialization point for resource {resource_id!r}, "
                        "but no `users`/`rate` declaration's demand reaches "
                        "it -- the utilization check cannot be silently "
                        "skipped (fail-closed, T-0703)"
                    ),
                )
            )
            continue
        capacity, capacity_declared = _capacity_per_second(node)
        utilization = demand.value / capacity if capacity > 0 else float("inf")
        if utilization <= 1.0:
            _log.debug(
                "starvation: node %s resource %s utilization %.4f <= 1.0, clean",
                node_id,
                resource_id,
                utilization,
            )
            continue
        capacity_source = (
            "declared capacity"
            if capacity_declared
            else (f"default holding time {_DEFAULT_HOLDING_TIME_SECONDS}s")
        )
        _log.warning(
            "starvation: REL380 node %s resource %s demand=%s/s capacity=%s/s "
            "(%s) utilization=%.2fx",
            node_id,
            resource_id,
            demand.value,
            capacity,
            capacity_source,
            utilization,
        )
        violations.append(
            StarvationViolation(
                rule=REL_SERIALIZATION_UTILIZATION,
                node=node_id,
                resource=resource_id,
                sub_target=resource_id,
                detail=(
                    f"node {node_id!r} serialization point for resource "
                    f"{resource_id!r}: demand={demand.value:g}/s, "
                    f"capacity={capacity:g}/s ({capacity_source}), "
                    f"utilization={utilization:.2f}x capacity (> 1.0x)"
                ),
            )
        )
    return violations


def _writer_starvation_violations(
    model: KernelModel,
) -> list[StarvationViolation]:
    """REL382: every resource with >=1 `read` accessor and >=1 write-like
    accessor (`_WRITE_LIKE_MODES`) but NO `alpha` accessor declared --
    fires once per (write-like accessor node, resource) pair so the
    finding names a concrete node to fix, mirroring REL380/REL381's
    per-accessor reporting shape rather than a bare per-resource one."""
    violations: list[StarvationViolation] = []
    accessors = _resource_accessors(model)
    for resource_id in sorted(accessors):
        pairs = accessors[resource_id]
        has_reader = any(mode == AccessMode.READ for _node, mode in pairs)
        has_alpha = any(mode == AccessMode.ALPHA for _node, mode in pairs)
        if not has_reader or has_alpha:
            continue
        writers = sorted(
            node_id for node_id, mode in pairs if mode in _WRITE_LIKE_MODES
        )
        for node_id in writers:
            _log.warning(
                "starvation: REL382 resource %s is read-heavy with writer "
                "%s and no alpha/fairness accessor declared",
                resource_id,
                node_id,
            )
            violations.append(
                StarvationViolation(
                    rule=REL_WRITER_STARVATION,
                    node=node_id,
                    resource=resource_id,
                    sub_target=resource_id,
                    detail=(
                        f"resource {resource_id!r} has read accessor(s) and "
                        f"write-like accessor {node_id!r}, but no `alpha` "
                        "accessor declared -- readers can perpetually "
                        "preempt the writer (recommend an `alpha` upgrade "
                        "path or fair queuing, T-0703 advisory)"
                    ),
                )
            )
    return violations


def _unbounded_wait_violations(
    model: KernelModel,
) -> list[StarvationViolation]:
    """REL383: every node accessing a CONTENDED resource (2+ total
    accessors of the same resource id) in a write-like/alpha mode with no
    `timeout` attr declared on the accessing node itself -- deny-by-
    default, the same T-0640 TIMEOUT vocabulary reapplied at this
    module's own population (module docstring family (3))."""
    violations: list[StarvationViolation] = []
    accessors = _resource_accessors(model)
    node_by_id = {node.id: node for node in model.nodes}
    for resource_id in sorted(accessors):
        pairs = accessors[resource_id]
        if len(pairs) < 2:
            continue
        for node_id, mode in sorted(pairs):
            if mode not in _SERIALIZATION_MODES:
                continue
            node = node_by_id.get(node_id)
            if node is None or _TIMEOUT_ATTR in node.attrs:
                continue
            _log.warning(
                "starvation: REL383 node %s acquires contended resource %s "
                "in mode %s with no declared timeout",
                node_id,
                resource_id,
                mode,
            )
            violations.append(
                StarvationViolation(
                    rule=REL_UNBOUNDED_WAIT,
                    node=node_id,
                    resource=resource_id,
                    sub_target=resource_id,
                    detail=(
                        f"node {node_id!r} acquires contended resource "
                        f"{resource_id!r} (mode={mode.value}) with no "
                        "declared timeout -- unbounded wait on acquisition "
                        "(T-0703, joins the T-0640 TIMEOUT obligation family)"
                    ),
                )
            )
    return violations


def _apply_starvation_waivers(
    model: KernelModel, violations: list[StarvationViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_reliability.py::_apply_reliability_waivers`'s pattern reused for the
    REL38x family, scoped to this module's OWN `STARVATION_RULES` (never
    a shared cross-family superset -- the real regression `_reliability.
    py`'s module docstring documents for why each caller passes its own
    slice)."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in STARVATION_RULES,
    )


# frob:doc docs/strata/reliability.md#rel38x-starvationthroughput-obligation-t-0703
# frob:ticket T-0703
# frob:tests tests/unit/strata/test_starvation.py::TestUtilization.test_over_capacity_demand_fires_with_arithmetic  # noqa: E501
def check_starvation_obligations(
    model: KernelModel, module: Module, facts: FactBase
) -> StarvationReport:
    """The REL38x STARVATION/THROUGHPUT-obligation entrypoint (T-0703):
    REL380/REL381 (serialization-point utilization/demand-undeclared),
    REL382 (writer starvation advisory), REL383 (unbounded wait) across
    every resource `model`/`module` declare, waivers already applied.
    `module` is the pre-elaboration `Module` (parsed AST) purely to reach
    `Module.resources` (the same "caller passes in what elaboration
    cannot reconstruct" shape `_access.py::resource_contention_violations`
    already established for SYS204); `facts` is the `FactBase` built over
    `model` (`build_facts`) that `aggregate_demand` needs. Unlike every
    proof-against-code REL2xx/REL3xx entrypoint, this takes no `root`/
    `bind_code` call and returns a bare `StarvationReport`, not a
    `Result` -- every REL38x rule is a structural/arithmetic read of the
    kernel model and its fact base (mirrors `_spof.py::check_spof`'s
    honest non-`Result` shape), never a proof against source code."""
    violations: list[StarvationViolation] = []
    violations.extend(_utilization_violations(model, module, facts))
    violations.extend(_writer_starvation_violations(model))
    violations.extend(_unbounded_wait_violations(model))
    applied = _apply_starvation_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        StarvationViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            resource="",
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
        "starvation: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return StarvationReport(violations=tuple(applied.kept) + stale, waived=waived)


__all__ = [
    "REL_SERIALIZATION_DEMAND_UNDECLARED",
    "REL_SERIALIZATION_UTILIZATION",
    "REL_UNBOUNDED_WAIT",
    "REL_WRITER_STARVATION",
    "STARVATION_RULES",
    "StarvationReport",
    "StarvationViolation",
    "check_starvation_obligations",
]
