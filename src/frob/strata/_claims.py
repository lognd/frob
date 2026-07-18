"""Claim evaluation for the strata kernel (docs/strata/kernel.md).

Turns each `Claim` into a `ClaimResult` with a quantifier-tagged verdict
and, on refutation, a witness path or number -- never a vibe (charter
law 4). Assumes close as ASSUMED (law 3); everything else is proved or
refuted against the `FactBase` closure, which is complete over the model.
"""

# frob:waive TEST005 reason="module line coverage 84.7%, debt T-0160"

from __future__ import annotations

import calendar
import datetime as _dt
import math

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import FactBase, build_facts
from ._models import (
    BoundClaim,
    Claim,
    ClaimResult,
    Independent,
    KernelModel,
    Metric,
    NoFlow,
    Quantifier,
    Quantity,
    Reach,
    SetEquality,
    Verdict,
)
from ._packs import EXTRACTION_SOUNDNESS
from ._policy import CompiledPolicies

_log = get_logger(__name__)

#: Node attr prefix for zipf skew (surface `skew zipf NUM`).
_SKEW_PREFIX = "skew="
#: Flow attr prefix for monthly compound growth (surface `growth NUM %`).
_GROWTH_PREFIX = "growth="
#: Deny-by-default saturation horizon (months); a PROVED utilization whose
#: growth-projected saturation falls within this window is REFUTED instead
#: (docs/strata/kernel.md#capacity-semantics).
_GROWTH_HORIZON_MONTHS = 24


def _node_skew(node) -> float | None:
    """A node's zipf skew exponent: its `skew=<alpha>` attr, or None."""
    # frob:doc docs/strata/kernel.md#capacity-semantics
    for attr in node.attrs:
        if attr.startswith(_SKEW_PREFIX):
            try:
                return float(attr[len(_SKEW_PREFIX) :])
            except ValueError:
                _log.warning("node %s: malformed skew attr %r", node.id, attr)
                return None
    return None


def _zipf_hottest_share(alpha: float, shards: int) -> float:
    """The rank-1 zipf share among `shards` replicas at skew exponent `alpha`.

    `hottest_share = (1/1^alpha) / sum_{k=1..shards} (1/k^alpha)` --
    docs/strata/kernel.md#capacity-semantics.
    """
    # frob:doc docs/strata/kernel.md#capacity-semantics
    weights = [1.0 / (k**alpha) for k in range(1, max(shards, 1) + 1)]
    return weights[0] / sum(weights)


def _flow_growth(flow) -> float | None:
    """A flow's declared monthly growth percent: its `growth=<pct>` attr, or None."""
    # frob:doc docs/strata/kernel.md#capacity-semantics
    for attr in flow.attrs:
        if attr.startswith(_GROWTH_PREFIX):
            try:
                return float(attr[len(_GROWTH_PREFIX) :])
            except ValueError:
                _log.warning("flow %s: malformed growth attr %r", flow.id, attr)
                return None
    return None


def _add_months(d: _dt.date, months: int) -> _dt.date:
    """`d` advanced by `months` whole months, clamping the day to the target month."""
    # frob:doc docs/strata/kernel.md#capacity-semantics
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return _dt.date(year, month, day)


def _months_to_saturation(
    utilization0: float, limit: float, growth_pct: float
) -> float | None:
    """Months of compound monthly growth until `utilization0` crosses `limit`.

    None when it never crosses (already >= limit, non-positive utilization,
    or non-positive growth).
    """
    # frob:doc docs/strata/kernel.md#capacity-semantics
    if utilization0 <= 0.0 or utilization0 >= limit or growth_pct <= 0.0:
        return None
    g = growth_pct / 100.0
    return math.log(limit / utilization0) / math.log(1.0 + g)


def _expand(facts: FactBase, ref: str) -> Result[tuple[str, ...], StrataError]:
    """A claim endpoint is a node id or a trust level; anything else fails closed."""
    if ref in facts.nodes:
        return Ok((ref,))
    if ref in facts.model.trust.elements():
        return Ok(facts.nodes_at(ref))
    _log.error("claim endpoint %r is neither a node nor a trust level", ref)
    return Err(StrataError.UnknownReference)


def _eval_noflow(
    facts: FactBase, claim: Claim, body: NoFlow
) -> Result[ClaimResult, StrataError]:
    """REFUTED with the first witness path; PROVED forall when the closure is empty."""
    sources = _expand(facts, body.src)
    if sources.is_err:
        return Err(sources.danger_err)
    targets = _expand(facts, body.dst)
    if targets.is_err:
        return Err(targets.danger_err)
    target_set = set(targets.danger_ok)
    sorted_targets = sorted(target_set)  # hoisted above every loop below
    for src in sources.danger_ok:
        paths = facts.reachable(src)
        for dst in sorted_targets:
            if dst in paths and dst != src:
                _log.info("noflow %s refuted: %s", claim.id, paths[dst])
                return Ok(
                    ClaimResult(
                        claim_id=claim.id,
                        verdict=Verdict.REFUTED,
                        quantifier=Quantifier.FORALL,
                        counterexample=paths[dst],
                        detail=f"influence path {src} -> {dst} with no boundary",
                    )
                )
    return Ok(
        ClaimResult(
            claim_id=claim.id,
            verdict=Verdict.PROVED,
            quantifier=Quantifier.FORALL,
            detail="no unendorsed influence path exists",
        )
    )


def _eval_reach(
    facts: FactBase, claim: Claim, body: Reach
) -> Result[ClaimResult, StrataError]:
    """PROVED (exists) with a witness path; its refutation is a forall (no path)."""
    sources = _expand(facts, body.src)
    if sources.is_err:
        return Err(sources.danger_err)
    targets = _expand(facts, body.dst)
    if targets.is_err:
        return Err(targets.danger_err)
    target_set = set(targets.danger_ok)
    sorted_targets = sorted(target_set)  # hoisted above every loop below
    for src in sources.danger_ok:
        paths = facts.reachable(src, through_barriers=True)
        for dst in sorted_targets:
            if dst in paths:
                return Ok(
                    ClaimResult(
                        claim_id=claim.id,
                        verdict=Verdict.PROVED,
                        quantifier=Quantifier.EXISTS,
                        counterexample=paths[dst],
                        detail="witness path",
                    )
                )
    _log.info("reach %s refuted: no path %s -> %s", claim.id, body.src, body.dst)
    return Ok(
        ClaimResult(
            claim_id=claim.id,
            verdict=Verdict.REFUTED,
            quantifier=Quantifier.FORALL,
            detail=f"no path {body.src} -> {body.dst} exists",
        )
    )


def _eval_independent(
    facts: FactBase, claim: Claim, body: Independent
) -> Result[ClaimResult, StrataError]:
    """`independent(p, n)`: PROVED forall when no src->dst witness path touches
    avoid's reach closure; REFUTED with the offending path on the first overlap
    (docs/strata/kernel.md#claim-forms-and-their-decision-procedures, T-0076).

    `avoid` itself is excluded from its own closure before comparing: a
    recovery path is expected to terminate AT the node it recovers, so
    `dst == avoid` (the common breach case) must not trivially refute
    every claim -- what independence forbids is the path touching
    anything ELSE `avoid` can also reach.
    """
    sources = _expand(facts, body.src)
    if sources.is_err:
        return Err(sources.danger_err)
    targets = _expand(facts, body.dst)
    if targets.is_err:
        return Err(targets.danger_err)
    avoided = _expand(facts, body.avoid)
    if avoided.is_err:
        return Err(avoided.danger_err)
    sorted_targets = sorted(targets.danger_ok)  # hoisted above every loop below
    avoid_roots = set(avoided.danger_ok)
    avoid_nodes: set[str] = set()
    for avoid_src in avoided.danger_ok:
        avoid_nodes |= set(facts.reachable(avoid_src, through_barriers=True))
    avoid_nodes -= avoid_roots
    for src in sources.danger_ok:
        paths = facts.reachable(src, through_barriers=True)
        for dst in sorted_targets:
            if dst not in paths:
                continue
            path = paths[dst]
            shared = set(path[0::2]) & avoid_nodes
            if shared:
                offending = min(shared)  # deterministic without a per-iteration sort
                _log.info(
                    "independent %s refuted: path %s shares node %s with "
                    "avoided closure %s",
                    claim.id,
                    path,
                    offending,
                    body.avoid,
                )
                return Ok(
                    _refuted(
                        claim, f"path shares node {offending} with {body.avoid}", path
                    )
                )
    return Ok(_proved(claim, f"no witness path shares a node with {body.avoid}"))


def _eval_set_equality(
    facts: FactBase, claim: Claim, body: SetEquality
) -> Result[ClaimResult, StrataError]:
    """`readers(target) == expected`: PROVED forall on an exact closure match.

    Uses the same forward, barrier-respecting closure `reach` uses
    (docs/strata/kernel.md#claim-forms-and-their-decision-procedures) --
    `std.secrets`'s consuming case is exactly "every node this credential's
    own flow chain reaches", so no new traversal is built here, only a set
    comparison against it. REFUTED reports both directions of the mismatch
    (extra readers the closure reaches but `expected` did not declare, and
    missing readers `expected` declared but the closure never reaches) so a
    counterexample is self-explanatory without re-deriving the closure.
    """
    if body.target not in facts.nodes:
        _log.error("readers claim %s: unknown target %r", claim.id, body.target)
        return Err(StrataError.UnknownReference)
    # frob:waive PERF004 reason="sorted() runs once after this loop, not inside it"
    for reader in body.expected:
        if reader not in facts.nodes:
            _log.error("readers claim %s: unknown expected reader %r", claim.id, reader)
            return Err(StrataError.UnknownReference)
    paths = facts.reachable(body.target, through_barriers=True)
    actual = frozenset(paths) - {body.target}
    expected = frozenset(body.expected)
    if actual == expected:
        return Ok(_proved(claim, f"readers({body.target}) == {sorted(expected)}"))
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    _log.info(
        "readers claim %s refuted: target=%s extra=%s missing=%s",
        claim.id,
        body.target,
        extra,
        missing,
    )
    detail = f"readers({body.target}) mismatch: extra={extra} missing={missing}"
    return Ok(_refuted(claim, detail, tuple(extra) + tuple(missing)))


def _limit_in(limit: Quantity, dimension: str) -> Result[float, StrataError]:
    """The bound's limit in base units, refusing a limit of the wrong dimension."""
    dim = limit.dimension()
    if dim.is_err:
        return Err(dim.danger_err)
    if dim.danger_ok != dimension:
        _log.error("bound limit %s%s is not %s", limit.value, limit.unit, dimension)
        return Err(StrataError.UnitMismatch)
    return Ok(limit.base_value().danger_ok)


def _refuted(claim: Claim, detail: str, path: tuple[str, ...] = ()) -> ClaimResult:
    """Deny-by-default refutation helper: missing declarations never pass."""
    return ClaimResult(
        claim_id=claim.id,
        verdict=Verdict.REFUTED,
        quantifier=Quantifier.FORALL,
        counterexample=path,
        detail=detail,
    )


def _proved(claim: Claim, detail: str) -> ClaimResult:
    """A forall PROVED result with its numeric justification in the detail."""
    return ClaimResult(
        claim_id=claim.id,
        verdict=Verdict.PROVED,
        quantifier=Quantifier.FORALL,
        detail=detail,
    )


def _eval_bound(
    facts: FactBase, claim: Claim, body: BoundClaim, today: _dt.date
) -> Result[ClaimResult, StrataError]:
    """Arithmetic bounds: age/rate/utilization on nodes, latency/size on flows."""
    if body.metric is Metric.AGE:
        if body.target not in facts.nodes:
            return Err(StrataError.UnknownReference)
        limit = _limit_in(body.limit, "time")
        if limit.is_err:
            return Err(limit.danger_err)
        age, path = facts.worst_age(body.target)
        if age == float("inf"):
            return Ok(_refuted(claim, "staleness unbounded: positive-age cycle", path))
        if age > limit.danger_ok:
            return Ok(_refuted(claim, f"worst age {age}s > {limit.danger_ok}s", path))
        return Ok(_proved(claim, f"worst age {age}s <= {limit.danger_ok}s"))

    if body.metric is Metric.RATE:
        if body.target not in facts.nodes:
            return Err(StrataError.UnknownReference)
        limit = _limit_in(body.limit, "rate")
        if limit.is_err:
            return Err(limit.danger_err)
        demand = facts.demand(body.target)
        if demand > limit.danger_ok:
            return Ok(_refuted(claim, f"demand {demand}/s > {limit.danger_ok}/s"))
        return Ok(_proved(claim, f"demand {demand}/s <= {limit.danger_ok}/s"))

    if body.metric is Metric.UTILIZATION:
        node = facts.nodes.get(body.target)
        if node is None:
            return Err(StrataError.UnknownReference)
        limit = _limit_in(body.limit, "percent")
        if limit.is_err:
            return Err(limit.danger_err)
        if node.capacity is None:
            return Ok(_refuted(claim, f"{node.id} declares no capacity"))
        rate = node.capacity.service_rate.base_value()
        if rate.is_err:
            return Err(rate.danger_err)
        single_rate = rate.danger_ok
        demand = facts.demand(body.target)
        skew_alpha = _node_skew(node)
        if skew_alpha is not None:
            if single_rate <= 0:
                return Ok(_refuted(claim, f"{node.id} has zero service ceiling"))
            hottest_share = _zipf_hottest_share(skew_alpha, node.capacity.replicas_max)
            utilization = 100.0 * demand * hottest_share / single_rate
            over_detail = (
                f"utilization {utilization:.1f}% > {limit.danger_ok}% "
                f"at hottest-shard share {hottest_share:.4f} "
                f"(zipf alpha={skew_alpha}, {node.capacity.replicas_max} shards)"
            )
            ok_detail = (
                f"utilization {utilization:.1f}% <= {limit.danger_ok}% "
                f"at hottest-shard share {hottest_share:.4f}"
            )
        else:
            ceiling = single_rate * node.capacity.replicas_max
            if ceiling <= 0:
                return Ok(_refuted(claim, f"{node.id} has zero service ceiling"))
            utilization = 100.0 * demand / ceiling
            over_detail = (
                f"utilization {utilization:.1f}% > {limit.danger_ok}% "
                f"at max replicas {node.capacity.replicas_max}"
            )
            ok_detail = f"utilization {utilization:.1f}% <= {limit.danger_ok}%"
        if utilization > limit.danger_ok:
            return Ok(_refuted(claim, over_detail))

        growth_pct: float | None = None
        for f in facts.flows.values():
            if f.dst != body.target:
                continue
            g = _flow_growth(f)
            if g is not None and (growth_pct is None or g > growth_pct):
                growth_pct = g
        if growth_pct is not None:
            months = _months_to_saturation(utilization, limit.danger_ok, growth_pct)
            if months is not None and months <= _GROWTH_HORIZON_MONTHS:
                horizon = math.ceil(months)
                sat_date = _add_months(today, horizon)
                _log.warning(
                    "bound %s: utilization %s saturates in %s month(s) "
                    "(growth=%s%%/mo)",
                    claim.id,
                    body.target,
                    horizon,
                    growth_pct,
                )
                return Ok(
                    _refuted(
                        claim,
                        f"saturates in {horizon} months ({sat_date.isoformat()[:7]})",
                    )
                )
        return Ok(_proved(claim, ok_detail))

    # LATENCY / SIZE: direct comparison against the flow's declared quantity.
    flow = facts.flows.get(body.target)
    if flow is None:
        return Err(StrataError.UnknownReference)
    declared = flow.size if body.metric is Metric.SIZE else None
    if declared is None:
        return Ok(
            _refuted(claim, f"{flow.id} declares no {body.metric.value} to check")
        )
    verdict = declared.leq(body.limit)
    if verdict.is_err:
        return Err(verdict.danger_err)
    if not verdict.danger_ok:
        return Ok(
            _refuted(
                claim,
                f"declared {body.metric.value} {declared.value}{declared.unit} "
                f"exceeds {body.limit.value}{body.limit.unit}",
            )
        )
    return Ok(_proved(claim, f"declared {body.metric.value} within limit"))


def _eval_assumed(claim: Claim, today: _dt.date) -> ClaimResult:
    """Assumes never prove anything; they are ledgered, owned, and expiring."""
    detail = f"assumed by {claim.owner or 'unowned'}"
    if claim.review is not None:
        try:
            review = _dt.date.fromisoformat(claim.review)
        except ValueError:
            _log.warning(
                "assume %s has malformed review date %r", claim.id, claim.review
            )
            detail += "; review date malformed"
        else:
            if review < today:
                _log.warning("assume %s review overdue (%s)", claim.id, claim.review)
                detail += f"; review overdue since {claim.review}"
            else:
                detail += f"; review by {claim.review}"
    return ClaimResult(
        claim_id=claim.id,
        verdict=Verdict.ASSUMED,
        quantifier=Quantifier.FORALL,
        detail=detail,
    )


def _cascade_detail(
    compiled_policies: CompiledPolicies | None, waived_policies: frozenset[str]
) -> str | None:
    """The downgrade detail string when a waived policy enables extraction_soundness.

    v0 dependency rule (docs/strata/evidence.md#the-enables-cascade): all
    noflow and reach claims depend on `extraction_soundness`; bound claims
    do not. Picking the lexicographically-first enabling policy id keeps
    the detail deterministic when several waived policies enable the same
    atom.
    """
    if compiled_policies is None or not waived_policies:
        return None
    enabling_ids = sorted(
        p.id
        for p in compiled_policies.policies
        if p.id in waived_policies and EXTRACTION_SOUNDNESS in p.enables
    )
    if not enabling_ids:
        return None
    return f"soundness dependency {EXTRACTION_SOUNDNESS} waived via {enabling_ids[0]}"


# frob:doc docs/strata/kernel.md#claim-evaluation
def evaluate_claims(
    model: KernelModel,
    *,
    today: _dt.date | None = None,
    compiled_policies: CompiledPolicies | None = None,
    waived_policies: frozenset[str] = frozenset(),
) -> Result[tuple[ClaimResult, ...], StrataError]:
    """Evaluate every claim in the model against the tier-1 closure.

    Fails closed on a malformed model or claim reference; otherwise every
    claim yields exactly one result, in declaration order, so a report can
    never silently drop a claim. When `waived_policies` names an id in
    `compiled_policies` that `enables extraction_soundness`, every PROVED
    noflow/reach/independent/readers(set-equality) verdict downgrades to
    ASSUMED with a detail recording which policy waiver caused it --
    quantifier-preserving, logged at WARNING per affected claim
    (docs/strata/evidence.md#the-enables-cascade). Bound claims never depend
    on this atom in v0 and are never downgraded by it.
    """
    facts_result = build_facts(model)
    if facts_result.is_err:
        return Err(facts_result.danger_err)
    facts = facts_result.danger_ok
    current = today or _dt.date.today()
    cascade_detail = _cascade_detail(compiled_policies, waived_policies)

    results: list[ClaimResult] = []
    for claim in model.claims:
        if claim.assumed:
            results.append(_eval_assumed(claim, current))
            continue
        body = claim.body
        if isinstance(body, NoFlow):
            outcome = _eval_noflow(facts, claim, body)
        elif isinstance(body, Reach):
            outcome = _eval_reach(facts, claim, body)
        elif isinstance(body, Independent):
            outcome = _eval_independent(facts, claim, body)
        elif isinstance(body, SetEquality):
            outcome = _eval_set_equality(facts, claim, body)
        else:
            outcome = _eval_bound(facts, claim, body, current)
        if outcome.is_err:
            return Err(outcome.danger_err)
        result = outcome.danger_ok
        if (
            cascade_detail is not None
            and isinstance(body, NoFlow | Reach | Independent | SetEquality)
            and result.verdict is Verdict.PROVED
        ):
            _log.warning(
                "claim %s downgraded PROVED -> ASSUMED: %s", claim.id, cascade_detail
            )
            result = result.model_copy(
                update={"verdict": Verdict.ASSUMED, "detail": cascade_detail}
            )
        results.append(result)
    _log.info(
        "evaluated %d claim(s): %s",
        len(results),
        {v.value: sum(1 for r in results if r.verdict is v) for v in Verdict},
    )
    return Ok(tuple(results))
