"""Claim evaluation for the strata kernel (docs/strata/kernel.md).

Turns each `Claim` into a `ClaimResult` with a quantifier-tagged verdict
and, on refutation, a witness path or number -- never a vibe (charter
law 4). Assumes close as ASSUMED (law 3); everything else is proved or
refuted against the `FactBase` closure, which is complete over the model.
"""

from __future__ import annotations

import datetime as _dt

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import FactBase, build_facts
from ._models import (
    BoundClaim,
    Claim,
    ClaimResult,
    KernelModel,
    Metric,
    NoFlow,
    Quantifier,
    Quantity,
    Reach,
    Verdict,
)

_log = get_logger(__name__)


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
    for src in sources.danger_ok:
        paths = facts.reachable(src)
        for dst in sorted(target_set):
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
    for src in sources.danger_ok:
        paths = facts.reachable(src, through_barriers=True)
        for dst in sorted(target_set):
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
    facts: FactBase, claim: Claim, body: BoundClaim
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
        ceiling = rate.danger_ok * node.capacity.replicas_max
        if ceiling <= 0:
            return Ok(_refuted(claim, f"{node.id} has zero service ceiling"))
        utilization = 100.0 * facts.demand(body.target) / ceiling
        if utilization > limit.danger_ok:
            return Ok(
                _refuted(
                    claim,
                    f"utilization {utilization:.1f}% > {limit.danger_ok}% "
                    f"at max replicas {node.capacity.replicas_max}",
                )
            )
        return Ok(
            _proved(claim, f"utilization {utilization:.1f}% <= {limit.danger_ok}%")
        )

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


# frob:doc docs/strata/kernel.md#claim-evaluation
def evaluate_claims(
    model: KernelModel, *, today: _dt.date | None = None
) -> Result[tuple[ClaimResult, ...], StrataError]:
    """Evaluate every claim in the model against the tier-1 closure.

    Fails closed on a malformed model or claim reference; otherwise every
    claim yields exactly one result, in declaration order, so a report can
    never silently drop a claim.
    """
    facts_result = build_facts(model)
    if facts_result.is_err:
        return Err(facts_result.danger_err)
    facts = facts_result.danger_ok
    current = today or _dt.date.today()

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
        else:
            outcome = _eval_bound(facts, claim, body)
        if outcome.is_err:
            return Err(outcome.danger_err)
        results.append(outcome.danger_ok)
    _log.info(
        "evaluated %d claim(s): %s",
        len(results),
        {v.value: sum(1 for r in results if r.verdict is v) for v in Verdict},
    )
    return Ok(tuple(results))
