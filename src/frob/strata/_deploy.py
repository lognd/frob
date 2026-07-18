"""Deploy contracts for the strata kernel (docs/strata/surface.md#std-deploy, T-0083).

A node's `on deploy { canary { ... }; endorsed_by X, Y; rollback within t }`
contract desugars to two joined checks plus one generation step, following
the crash-contract precedent (T-0074) exactly: validate, then reuse the
existing scenario/rewrite machinery rather than a parallel evaluator.

1. **Endorsement-chain validation.** `endorsement_chain` names upstream
   `Boundary` ids an artifact must have already crossed (review/build/admit,
   docs/strata/boundary.md) before this node may deploy it. Every named id
   must exist and be `endorse`-directed; a missing or wrong-direction
   boundary fails closed (`MissingEndorsement` / `IncompatibleEndorsement`)
   rather than silently accepting an unreviewed artifact -- the same
   deny-by-default posture the crash contract's no-hang check uses.
2. **Canary-level validation.** Every stage's `level` must be a real level
   in the model's trust lattice, else `Lattice.leq` already returns
   `UnknownLevel` -- reused, never re-derived.
3. **Auto-generated scenarios.** Canary = staged trust escalation: one
   `SetTrust` scenario per stage, re-checking every declared claim exactly
   like `_crash.py`'s auto-generated node-loss scenarios. Each stage's
   scenario is evaluated INDEPENDENTLY against a fresh copy of `model` --
   `evaluate_scenarios` rewrites and re-checks per scenario, so stage 2
   never sees stage 1's `SetTrust` already applied; this is a snapshot of
   "the model with only this stage's promotion," not a cumulative replay
   of the whole schedule. Rollback budget = bounded recovery scenario: the
   same `RemoveNode` total-loss rewrite `on crash` uses, since a rollback
   and a crash are both "this node's current state is gone, does the rest
   of the model still hold." Both are handed to `_scenarios.py::
   evaluate_scenarios`, never a parallel evaluator.

Surface grammar deferral (T-0132 precedent): v0's `.strata` parser has no
`on deploy { ... }` construct yet -- the same class of gap T-0132 filed for
`code=`/`may` (strata-core's lexer has no multi-value block syntax for a
canary schedule or an endorsement-chain list). This module is kernel-level
only, exercised directly against a hand-built `KernelModel`/`DeployContract`
exactly as `_crash.py` and `_atomic.py` were before their surface syntax
landed. Filed as T-0134.
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._models import (
    BoundaryDirection,
    Claim,
    KernelModel,
    Node,
    RemoveNode,
    Scenario,
    SetTrust,
)
from ._policy import CompiledPolicies
from ._scenarios import ScenarioResult, evaluate_scenarios

_log = get_logger(__name__)


# frob:doc docs/strata/surface.md#std-deploy
class DeployContractReport(BaseModel):
    """The joined output of every declared deploy contract's canary and rollback
    scenarios (docs/strata/surface.md#std-deploy, T-0083)."""

    model_config = ConfigDict(frozen=True)

    scenario_results: tuple[ScenarioResult, ...]


def _validate_endorsement_chain(
    model: KernelModel, deployable: dict[str, Node]
) -> Result[None, StrataError]:
    """Every `endorsement_chain` boundary id must exist and be `endorse`-directed.

    Fails closed (law 2): a deploy contract pointing at an undeclared
    boundary, or at a `declassify` boundary standing in for review/build/
    admit endorsement, is a dangling promise -- never silently accepted.
    """
    boundaries = {b.id: b for b in model.boundaries}
    for node in deployable.values():
        assert node.deploy is not None
        for boundary_id in node.deploy.endorsement_chain:
            boundary = boundaries.get(boundary_id)
            if boundary is None:
                _log.error(
                    "node %s: deploy endorsement_chain boundary %r is not declared",
                    node.id,
                    boundary_id,
                )
                return Err(StrataError.MissingEndorsement)
            if boundary.direction is not BoundaryDirection.ENDORSE:
                _log.error(
                    "node %s: deploy endorsement_chain boundary %s has "
                    "direction %s, not endorse",
                    node.id,
                    boundary_id,
                    boundary.direction,
                )
                return Err(StrataError.IncompatibleEndorsement)
    return Ok(None)


def _validate_canary_levels(
    model: KernelModel, deployable: dict[str, Node]
) -> Result[None, StrataError]:
    """Every canary stage's `level` must be a real trust-lattice level.

    Reuses `Lattice.leq` for the membership check (it already returns
    `UnknownLevel` on a typo) rather than re-deriving lattice membership.
    """
    for node in deployable.values():
        assert node.deploy is not None
        for stage in node.deploy.stages:
            leq = model.trust.leq(node.trust, stage.level)
            if leq.is_err:
                _log.error(
                    "node %s: canary stage level %r is not a known trust level",
                    node.id,
                    stage.level,
                )
                return Err(leq.danger_err)
    return Ok(None)


def _generate_canary_scenarios(
    deployable: dict[str, Node], node_ids: tuple[str, ...], claims: tuple[Claim, ...]
) -> tuple[Scenario, ...]:
    """One `SetTrust` staged-trust-escalation scenario per canary stage, in order.

    WHY: canary desugars to staged trust escalation (module docstring) --
    the existing `SetTrust` rewrite, reused rather than a parallel
    rollout-percentage mechanism. `node_ids` is caller-sorted once
    (`evaluate_deploy_contracts`), never re-sorted here, so a schedule
    with many deploying nodes does not re-pay the sort per generator.
    Node then stage order keeps generation deterministic.
    """
    scenarios: list[Scenario] = []
    for node_id in node_ids:
        node = deployable[node_id]
        assert node.deploy is not None
        for index, stage in enumerate(node.deploy.stages):
            scenarios.append(
                Scenario(
                    id=f"{node_id}__canary_{index}_{stage.level}",
                    rewrites=(SetTrust(node_id=node_id, level=stage.level),),
                    claims=claims,
                )
            )
    return tuple(scenarios)


def _generate_rollback_scenarios(
    node_ids: tuple[str, ...], claims: tuple[Claim, ...]
) -> tuple[Scenario, ...]:
    """One bounded-recovery (`RemoveNode`) scenario per deploying node.

    WHY: a rollback budget is a bound on recovering from "this node's
    current state is gone" -- the same total-loss counterfactual `on
    crash` already models, reused rather than a parallel rewrite kind
    (module docstring). `node_ids` is the same caller-sorted tuple
    `_generate_canary_scenarios` uses -- sorted once, not per generator.
    """
    return tuple(
        Scenario(
            id=f"{node_id}__rollback",
            rewrites=(RemoveNode(node_id=node_id),),
            claims=claims,
        )
        for node_id in node_ids
    )


def _validate_deploy_contracts(
    model: KernelModel, deployable: dict[str, Node]
) -> Result[None, StrataError]:
    """Both deploy-contract validation joins, endorsement chain first (module
    docstring)."""
    endorsement_ok = _validate_endorsement_chain(model, deployable)
    if endorsement_ok.is_err:
        return endorsement_ok
    return _validate_canary_levels(model, deployable)


def _evaluate_generated_scenarios(
    model: KernelModel,
    deployable: dict[str, Node],
    *,
    today: _dt.date | None,
    compiled_policies: CompiledPolicies | None,
    waived_policies: frozenset[str],
) -> Result[DeployContractReport, StrataError]:
    """Generate + evaluate canary/rollback scenarios for already-validated `deployable`
    (`node_ids` sorted once here, threaded into both generators)."""
    node_ids = tuple(sorted(deployable))
    generated = _generate_canary_scenarios(
        deployable, node_ids, model.claims
    ) + _generate_rollback_scenarios(node_ids, model.claims)
    scenario_model = model.model_copy(update={"scenarios": generated})
    scenarios = evaluate_scenarios(
        scenario_model,
        today=today,
        compiled_policies=compiled_policies,
        waived_policies=waived_policies,
    )
    if scenarios.is_err:
        return Err(scenarios.danger_err)
    _log.info(
        "evaluated %d deploy contract(s): %d scenario(s)",
        len(deployable),
        len(generated),
    )
    return Ok(DeployContractReport(scenario_results=scenarios.danger_ok))


# frob:doc docs/strata/surface.md#std-deploy
def evaluate_deploy_contracts(
    model: KernelModel,
    *,
    today: _dt.date | None = None,
    compiled_policies: CompiledPolicies | None = None,
    waived_policies: frozenset[str] = frozenset(),
) -> Result[DeployContractReport, StrataError]:
    """Validate, then generate + evaluate, every `on deploy` contract in `model`
    (fail closed, first error wins; no contracts is a valid empty report --
    docs/strata/surface.md#std-deploy, T-0083)."""
    deployable = {n.id: n for n in model.nodes if n.deploy is not None}
    if not deployable:
        _log.info("evaluate_deploy_contracts: no deploy contracts declared")
        return Ok(DeployContractReport(scenario_results=()))

    validated = _validate_deploy_contracts(model, deployable)
    if validated.is_err:
        return Err(validated.danger_err)

    return _evaluate_generated_scenarios(
        model,
        deployable,
        today=today,
        compiled_policies=compiled_policies,
        waived_policies=waived_policies,
    )
