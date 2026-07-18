"""Scenario evaluation for the strata kernel (docs/strata/kernel.md#scenario).

A scenario is a named counterfactual rewrite of the model -- node loss,
rate surge, trust downgrade -- under which a fresh set of claims is
re-checked (charter: "Zone failure, load surge, and component compromise
are one operation: rewrite part of the model, re-check every claim,
report what breaks"). This module owns exactly the rewrite step; claim
re-evaluation is delegated to the existing `evaluate_claims` machinery in
`_claims.py` so a scenario's claims are proved/refuted/assumed by the
same code path as ordinary claims, not a parallel one that could drift.
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._errors import StrataError
from ._models import (
    ClaimResult,
    KernelModel,
    RemoveNode,
    Rewrite,
    ScaleRate,
    Scenario,
    SetTrust,
)
from ._policy import CompiledPolicies

_log = get_logger(__name__)


# frob:doc docs/strata/kernel.md#scenario
# frob:doc docs/guides/extending/scenario-kinds.md#scenario-kinds
class ScenarioResult(BaseModel):
    """One scenario's claim results, in declaration order (never drops a claim)."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    results: tuple[ClaimResult, ...]


def _apply_remove(
    model: KernelModel, rewrite: RemoveNode
) -> Result[KernelModel, StrataError]:
    """Delete `rewrite.node_id` and cascade: its flows, then boundaries on those flows.

    WHY: a node that no longer exists cannot be the endpoint of a flow, and
    a boundary cannot sit on a flow that no longer exists -- leaving either
    behind would let the rewritten model reference ids the removal just
    deleted (docs/strata/kernel.md#scenario). Every cascade deletion is
    logged at INFO so a scenario's blast radius is auditable from the log
    alone. Fails closed (`UnknownReference`) when the target node is not in
    the model -- the elaborator already guarantees this for scenarios built
    from source, but `evaluate_scenarios` is a public kernel API a caller
    may also drive with a hand-built `KernelModel`/`Scenario`.
    """
    if rewrite.node_id not in {n.id for n in model.nodes}:
        _log.error(
            "scenario rewrite: remove target %r is not declared", rewrite.node_id
        )
        return Err(StrataError.UnknownReference)
    doomed_flow_ids = {
        f.id
        for f in model.flows
        if f.src == rewrite.node_id or f.dst == rewrite.node_id
    }
    for flow_id in sorted(doomed_flow_ids):
        _log.info(
            "scenario rewrite: removing node %s cascades to flow %s",
            rewrite.node_id,
            flow_id,
        )
    doomed_boundary_ids = {
        b.id for b in model.boundaries if b.flow_id in doomed_flow_ids
    }
    for boundary_id in sorted(doomed_boundary_ids):
        _log.info(
            "scenario rewrite: removing node %s cascades to boundary %s",
            rewrite.node_id,
            boundary_id,
        )
    _log.info("scenario rewrite: removed node %s", rewrite.node_id)
    return Ok(
        model.model_copy(
            update={
                "nodes": tuple(n for n in model.nodes if n.id != rewrite.node_id),
                "flows": tuple(f for f in model.flows if f.id not in doomed_flow_ids),
                "boundaries": tuple(
                    b for b in model.boundaries if b.id not in doomed_boundary_ids
                ),
            }
        )
    )


def _apply_scale(
    model: KernelModel, rewrite: ScaleRate
) -> Result[KernelModel, StrataError]:
    """Multiply the named flow's declared rate by `rewrite.factor`.

    Fails closed on a flow with no declared rate (`UnratedFlow`): a surge
    multiplier on a rate nobody declared is meaningless, not a silent
    `None * factor` (charter law 2, deny by default).
    """
    flows: list = list(model.flows)
    found = False
    for i, flow in enumerate(flows):
        if flow.id != rewrite.flow_id:
            continue
        found = True
        if flow.rate is None:
            _log.error(
                "scenario rewrite: scale target %r has no declared rate",
                rewrite.flow_id,
            )
            return Err(StrataError.UnratedFlow)
        new_rate = flow.rate.model_copy(
            update={"value": flow.rate.value * rewrite.factor}
        )
        _log.info(
            "scenario rewrite: scaling flow %s rate %s -> %s (factor %s)",
            rewrite.flow_id,
            flow.rate.value,
            new_rate.value,
            rewrite.factor,
        )
        flows[i] = flow.model_copy(update={"rate": new_rate})
    if not found:
        _log.error("scenario rewrite: scale target %r is not declared", rewrite.flow_id)
        return Err(StrataError.UnknownReference)
    return Ok(model.model_copy(update={"flows": tuple(flows)}))


def _apply_trust(
    model: KernelModel, rewrite: SetTrust
) -> Result[KernelModel, StrataError]:
    """Reassign the named node's `trust` field to `rewrite.level`."""
    nodes: list = list(model.nodes)
    found = False
    for i, node in enumerate(nodes):
        if node.id != rewrite.node_id:
            continue
        found = True
        _log.info(
            "scenario rewrite: node %s trust %s -> %s",
            rewrite.node_id,
            node.trust,
            rewrite.level,
        )
        nodes[i] = node.model_copy(update={"trust": rewrite.level})
    if not found:
        _log.error("scenario rewrite: trust target %r is not declared", rewrite.node_id)
        return Err(StrataError.UnknownReference)
    return Ok(model.model_copy(update={"nodes": tuple(nodes)}))


def _apply_rewrite(
    model: KernelModel, rewrite: Rewrite
) -> Result[KernelModel, StrataError]:
    """Dispatch one `Rewrite` to its apply function; never mutates `model` in place."""
    if isinstance(rewrite, RemoveNode):
        return _apply_remove(model, rewrite)
    if isinstance(rewrite, ScaleRate):
        return _apply_scale(model, rewrite)
    assert isinstance(rewrite, SetTrust)
    return _apply_trust(model, rewrite)


def _rewrite_model(
    model: KernelModel, scenario: Scenario
) -> Result[KernelModel, StrataError]:
    """Apply every rewrite in `scenario`, in declaration order, to a copy of `model`.

    The scenario's own claims replace the base model's claims -- the
    rewritten fact base is evaluated only against what this scenario
    declared, never against the base model's unrelated claims
    (docs/strata/kernel.md#scenario).
    """
    rewritten = model
    for rewrite in scenario.rewrites:
        applied = _apply_rewrite(rewritten, rewrite)
        if applied.is_err:
            return Err(applied.danger_err)
        rewritten = applied.danger_ok
    return Ok(rewritten.model_copy(update={"claims": scenario.claims}))


# frob:doc docs/strata/kernel.md#scenario
def evaluate_scenarios(
    model: KernelModel,
    *,
    today: _dt.date | None = None,
    compiled_policies: CompiledPolicies | None = None,
    waived_policies: frozenset[str] = frozenset(),
) -> Result[tuple[ScenarioResult, ...], StrataError]:
    """Evaluate every `Scenario` in `model` against its own rewritten fact base.

    For each scenario, in declaration order: apply its rewrites to a COPY
    of `model` (the input is never mutated), then run `evaluate_claims`
    over the rewritten model with the scenario's nested claims. Fails
    closed on the first rewrite or claim-evaluation error -- a scenario
    can never silently vanish from the report (docs/strata/kernel.md
    #scenario, T-0073).
    """
    results: list[ScenarioResult] = []
    for scenario in model.scenarios:
        rewritten = _rewrite_model(model, scenario)
        if rewritten.is_err:
            _log.error(
                "scenario %s: rewrite failed: %s", scenario.id, rewritten.danger_err
            )
            return Err(rewritten.danger_err)
        claims_result = evaluate_claims(
            rewritten.danger_ok,
            today=today,
            compiled_policies=compiled_policies,
            waived_policies=waived_policies,
        )
        if claims_result.is_err:
            return Err(claims_result.danger_err)
        results.append(
            ScenarioResult(scenario_id=scenario.id, results=claims_result.danger_ok)
        )
    _log.info("evaluated %d scenario(s)", len(results))
    return Ok(tuple(results))
