"""Breach scenarios for the strata kernel (docs/strata/kernel.md#scenario, T-0076).

Breach(X) is a trust rewrite -- the same `SetTrust` scenario rewrite
`_scenarios.py` already applies for trust downgrades, generated
automatically per node declaring `on breach { ... }`, exactly as
`_crash.py` auto-generates node-loss scenarios for `on crash`. This
module owns three joined checks:

1. **Blast radius.** The influence closure reachable from the breached
   node -- everything a compromised node could reach is what an
   attacker who owns it could reach -- computed via the existing
   `FactBase.reachable` kernel primitive (through boundaries, since a
   compromised identity is exactly the class of thing a boundary
   predicate can no longer be trusted to have stopped), never a
   parallel closure.
2. **Containment bounds.** `detect` and `revoke` are both mandatory
   (charter law 2: a detection SLA with no revocation bound, or vice
   versa, is half a containment story); an optional `credential_age`
   must not outlive the revocation bound, else a credential the node
   holds stays valid past containment -- the same age-without-
   invalidation gap the charter refuses everywhere else.
3. **Recovery-path independence.** `on breach { ... recovers_via X }`
   auto-generates an `independent(X -> node, avoid=node)` claim
   (docs/strata/kernel.md#claim-forms-and-their-decision-procedures) so
   the recovery mechanism's own path back into the breached node is
   checked against that node's blast radius by the SAME claim
   evaluator `_claims.py::_eval_independent` uses for hand-written
   claims, never a parallel independence check.
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import build_facts
from ._models import (
    Claim,
    Independent,
    KernelModel,
    Node,
    Scenario,
    SetTrust,
)
from ._policy import CompiledPolicies
from ._scenarios import ScenarioResult, evaluate_scenarios

_log = get_logger(__name__)

#: The built-in trust lattice's lowest level; a breach rewrites the
#: compromised node down to it (docs/strata/kernel.md#lattice-semantics).
_BREACH_TRUST_LEVEL = "foreign"


# frob:doc docs/strata/kernel.md#scenario
class BlastRadius(BaseModel):
    """One breached node's reach closure: everything its compromise could touch."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    reached: tuple[str, ...]  # sorted node ids, excludes node_id itself


# frob:doc docs/strata/kernel.md#scenario
class BreachContractReport(BaseModel):
    """The joined output of breach-scenario claim results and blast radii."""

    model_config = ConfigDict(frozen=True)

    scenario_results: tuple[ScenarioResult, ...]
    blast_radii: tuple[BlastRadius, ...]


def _validate_recovery_via(
    model: KernelModel, breachable: dict[str, Node]
) -> Result[None, StrataError]:
    """Every declared `recovers_via` must name a real node, else `UnknownReference`.

    Fails closed (law 2): a breach contract naming an undeclared recovery
    node is a dangling promise, not a silently accepted one -- the same
    check `_crash.py::_validate_recovery_sources` runs for `recovers_from`.
    """
    known = {n.id for n in model.nodes}
    for node in breachable.values():
        assert node.breach is not None
        target = node.breach.recovers_via
        if target is not None and target not in known:
            _log.error(
                "node %s: breach recovers_via target %r is not declared",
                node.id,
                target,
            )
            return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_containment_bounds(
    breachable: dict[str, Node],
) -> Result[None, StrataError]:
    """`detect` must not exceed `revoke`, and neither may `credential_age`.

    Fails closed (`IncompatibleContainmentBound`): a compromise you detect
    only after you would have already needed to revoke it, or a
    credential that outlives the revocation window, is a containment
    contract that cannot actually contain anything.
    """
    for node in breachable.values():
        contract = node.breach
        assert contract is not None
        detect_ok = contract.detect.leq(contract.revoke)
        if detect_ok.is_err:
            return Err(detect_ok.danger_err)
        if not detect_ok.danger_ok:
            _log.error(
                "node %s: detection SLA %s%s exceeds revocation bound %s%s "
                "(T-0076)",
                node.id,
                contract.detect.value,
                contract.detect.unit,
                contract.revoke.value,
                contract.revoke.unit,
            )
            return Err(StrataError.IncompatibleContainmentBound)
        if contract.credential_age is None:
            continue
        age_ok = contract.credential_age.leq(contract.revoke)
        if age_ok.is_err:
            return Err(age_ok.danger_err)
        if not age_ok.danger_ok:
            _log.error(
                "node %s: credential_age %s%s outlives revocation bound %s%s "
                "(T-0076)",
                node.id,
                contract.credential_age.value,
                contract.credential_age.unit,
                contract.revoke.value,
                contract.revoke.unit,
            )
            return Err(StrataError.IncompatibleContainmentBound)
    return Ok(None)


def _compute_blast_radii(
    model: KernelModel, breachable: dict[str, Node]
) -> Result[tuple[BlastRadius, ...], StrataError]:
    """`FactBase.reachable` from each breached node, in node-id order.

    `through_barriers=True`: a compromised identity is exactly the class
    of actor a boundary predicate can no longer be trusted to have
    stopped, so the blast radius is the closure over every edge, not
    only the ones a boundary didn't gate (docs/strata/kernel.md
    #fact-base, T-0076).
    """
    facts = build_facts(model)
    if facts.is_err:
        return Err(facts.danger_err)
    sorted_ids = sorted(breachable)  # hoisted above every loop below
    radii = tuple(
        BlastRadius(
            node_id=node_id,
            reached=tuple(
                sorted(
                    n
                    for n in facts.danger_ok.reachable(node_id, through_barriers=True)
                    if n != node_id
                )
            ),
        )
        for node_id in sorted_ids
    )
    return Ok(radii)


def _generate_breach_scenarios(
    model: KernelModel, breachable: dict[str, Node]
) -> tuple[Scenario, ...]:
    """One auto-generated trust-downgrade scenario per breachable node.

    A node declaring `recovers_via` gets its recovery-path-independence
    claim (`Independent(src=recovers_via, dst=node_id, avoid=node_id)`)
    appended to that scenario's claim list alongside every base-model
    claim, so it is re-checked by the same `evaluate_scenarios` path used
    for every other scenario claim rather than a parallel evaluator
    (docs/strata/kernel.md#scenario, T-0076).
    """
    node_ids = sorted(breachable)
    scenarios: list[Scenario] = []
    for node_id in node_ids:
        contract = breachable[node_id].breach
        assert contract is not None
        claims = model.claims
        if contract.recovers_via is not None:
            claims = (
                *claims,
                Claim(
                    id=f"{node_id}__recovery_independent",
                    body=Independent(
                        src=contract.recovers_via, dst=node_id, avoid=node_id
                    ),
                ),
            )
        scenarios.append(
            Scenario(
                id=f"{node_id}__breach",
                rewrites=(SetTrust(node_id=node_id, level=_BREACH_TRUST_LEVEL),),
                claims=claims,
            )
        )
    return tuple(scenarios)


# frob:doc docs/strata/kernel.md#scenario
def evaluate_breach_contracts(
    model: KernelModel,
    *,
    today: _dt.date | None = None,
    compiled_policies: CompiledPolicies | None = None,
    waived_policies: frozenset[str] = frozenset(),
) -> Result[BreachContractReport, StrataError]:
    """Validate and evaluate every `on breach` contract declared in `model`.

    Order (all fail closed, first error wins): recovery-target references
    resolve, then containment-bound consistency, then blast radii are
    computed over the ORIGINAL (unrewritten) model, then the
    auto-generated breach scenarios -- each carrying its own
    recovery-path-independence claim when declared -- are evaluated via
    `evaluate_scenarios`. A model with no breach contracts returns an
    empty report rather than an error -- breach contracts are opt-in,
    not implied by every node (docs/strata/kernel.md#scenario, T-0076).
    """
    breachable = {n.id: n for n in model.nodes if n.breach is not None}
    if not breachable:
        _log.info("evaluate_breach_contracts: no breach contracts declared")
        return Ok(BreachContractReport(scenario_results=(), blast_radii=()))

    recovery_ok = _validate_recovery_via(model, breachable)
    if recovery_ok.is_err:
        return Err(recovery_ok.danger_err)
    bounds_ok = _validate_containment_bounds(breachable)
    if bounds_ok.is_err:
        return Err(bounds_ok.danger_err)

    blast_radii = _compute_blast_radii(model, breachable)
    if blast_radii.is_err:
        return Err(blast_radii.danger_err)

    generated = _generate_breach_scenarios(model, breachable)
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
        "evaluated %d breach contract(s): %d scenario(s), blast radius sizes %s",
        len(breachable),
        len(generated),
        {r.node_id: len(r.reached) for r in blast_radii.danger_ok},
    )
    return Ok(
        BreachContractReport(
            scenario_results=scenarios.danger_ok, blast_radii=blast_radii.danger_ok
        )
    )
