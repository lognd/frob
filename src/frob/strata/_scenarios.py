"""Scenario evaluation for the strata kernel (docs/strata/kernel.md#scenario).

A scenario is a named counterfactual rewrite of the model -- node loss,
rate surge, trust downgrade -- under which a fresh set of claims is
re-checked (charter: "Zone failure, load surge, and component compromise
are one operation: rewrite part of the model, re-check every claim,
report what breaks"). This module owns exactly the rewrite step; claim
re-evaluation is delegated to the existing `evaluate_claims` machinery in
`_claims.py` so a scenario's claims are proved/refuted/assumed by the
same code path as ordinary claims, not a parallel one that could drift.

`build_compromised_user_scenario` (T-0256, docs/strata/host.md#movement-
impossibility-proofs) is the compromised-service-owner red-team scenario
HOST001/HOST002 (`_host_isolation.py`) need: it REUSES the existing
`SetTrust` rewrite (compromise is already "a node's trust downgrades to
foreign", the SAME primitive component compromise already uses) and
generates the scenario's `NoFlow(src="foreign", dst=<every node outside
the user's manifest slice>)` claims -- proving the compromised user's
blast radius is EXACTLY its own `HostManifest` slice, no wider.

## The REJECT-round fix: movement vectors must be IN the closure

A T-0256 review round REJECTED the first version of this builder for a
real soundness hole: `_facts.py::FactBase.reachable` (the engine every
`NoFlow` claim is proved or refuted over) walks ONLY declared `Flow`
edges -- it has NO dependency on `HostManifest` ownership. Two users
sharing a writable filesystem path with no DECLARED app `Flow` between
them would make HOST001 correctly fire (`shared-writable-path`) while
the SAME model's compromised-user scenario claim reported PROVED --
false blast-radius assurance, exactly the movement this ticket exists to
prove impossible, silently unproven.

The fix (not a narrowed claim, a real one): `_host_isolation.py::
host_movement_flows` derives the SAME sharing relations HOST001 detects
(shared writable path, shared reachable socket) as synthetic `Flow`
facts, and this builder wraps each one in the new `AddFlow` rewrite
(`_models.py`) so the scenario's REWRITTEN model's closure -- not the
base model's declared flows alone -- includes them. `NoFlow` is now
proved or refuted over the full movement surface HOST001 already
reasons about, not just the app-level flow graph. `AddFlow` is scenario-
scoped (applies only to this scenario's rewritten copy, never mutates
the base `KernelModel`'s own declared flows) -- charter law 1 still
holds (reuses the existing `Flow` fact shape, no new closure primitive
in `strata_core`), it is the Rewrite vocabulary, not the kernel, that
grew by one variant."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_scenarios.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._errors import StrataError
from ._host import host_manifest_for
from ._host_isolation import host_movement_flows
from ._krb import KrbDelegationKind, krb_manifest_for
from ._models import (
    AddFlow,
    Claim,
    ClaimResult,
    Flow,
    KernelModel,
    NoFlow,
    RemoveNode,
    Rewrite,
    ScaleRate,
    Scenario,
    SetTrust,
)
from ._policy import CompiledPolicies

_log = get_logger(__name__)

#: The trust level a compromised node's `SetTrust` rewrite downgrades to
#: -- the SAME `"foreign"` level `_threat.py::_FOREIGN_TRUST` and
#: `NoFlow.src == "foreign"`'s expansion already recognize model-wide
#: (`_claims.py`'s src expansion), so a compromised-owner scenario's
#: blast-radius claims need no bespoke trust level of their own.
_COMPROMISED_TRUST = "foreign"


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
    doomed_flow_ids, doomed_boundary_ids = _remove_cascade_ids(model, rewrite.node_id)
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


def _remove_cascade_ids(model: KernelModel, node_id: str) -> tuple[set[str], set[str]]:
    """The `(flow_ids, boundary_ids)` that removing `node_id` cascades to
    (its flows, then boundaries on those flows), logged at INFO for
    `_apply_remove`'s auditable-blast-radius contract."""
    doomed_flow_ids = {
        f.id for f in model.flows if f.src == node_id or f.dst == node_id
    }
    for flow_id in sorted(doomed_flow_ids):
        _log.info(
            "scenario rewrite: removing node %s cascades to flow %s", node_id, flow_id
        )
    doomed_boundary_ids = {
        b.id for b in model.boundaries if b.flow_id in doomed_flow_ids
    }
    for boundary_id in sorted(doomed_boundary_ids):
        _log.info(
            "scenario rewrite: removing node %s cascades to boundary %s",
            node_id,
            boundary_id,
        )
    return doomed_flow_ids, doomed_boundary_ids


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
        scaled = _scale_flow(flow, rewrite.factor)
        if scaled.is_err:
            return Err(scaled.danger_err)
        flows[i] = scaled.danger_ok
    if not found:
        _log.error("scenario rewrite: scale target %r is not declared", rewrite.flow_id)
        return Err(StrataError.UnknownReference)
    return Ok(model.model_copy(update={"flows": tuple(flows)}))


def _scale_flow(flow, factor: float) -> Result[object, StrataError]:  # noqa: ANN001
    """Return `flow` with its rate multiplied by `factor`, failing closed
    (`UnratedFlow`) if it has no declared rate -- `_apply_scale`'s
    per-flow rewrite step."""
    if flow.rate is None:
        _log.error("scenario rewrite: scale target %r has no declared rate", flow.id)
        return Err(StrataError.UnratedFlow)
    new_rate = flow.rate.model_copy(update={"value": flow.rate.value * factor})
    _log.info(
        "scenario rewrite: scaling flow %s rate %s -> %s (factor %s)",
        flow.id,
        flow.rate.value,
        new_rate.value,
        factor,
    )
    return Ok(flow.model_copy(update={"rate": new_rate}))


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


def _apply_add_flow(
    model: KernelModel, rewrite: AddFlow
) -> Result[KernelModel, StrataError]:
    """Append `rewrite.flow` to the rewritten model's flow set (T-0256,
    `_models.py::AddFlow`'s docstring) -- the ONE closure-visible way a
    scenario materializes a counterfactual movement edge (e.g.
    `_host_isolation.py::host_movement_flows`'s HostManifest-derived
    sharing relations) without a new `strata_core` closure primitive.

    Fails closed (`StrataError.DuplicateId`) on a flow id collision with
    an already-present flow -- silently overwriting a declared flow with
    a synthetic one would corrupt the base model's own facts, never
    accepted (charter law 2)."""
    if rewrite.flow.id in {f.id for f in model.flows}:
        _log.error(
            "scenario rewrite: add-flow target id %r already declared", rewrite.flow.id
        )
        return Err(StrataError.DuplicateId)
    _log.info(
        "scenario rewrite: added flow %s (%s -> %s)",
        rewrite.flow.id,
        rewrite.flow.src,
        rewrite.flow.dst,
    )
    return Ok(model.model_copy(update={"flows": (*model.flows, rewrite.flow)}))


def _apply_rewrite(
    model: KernelModel, rewrite: Rewrite
) -> Result[KernelModel, StrataError]:
    """Dispatch one `Rewrite` to its apply function; never mutates `model` in place."""
    if isinstance(rewrite, AddFlow):
        return _apply_add_flow(model, rewrite)
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


def _no_runs_as_error(user: str) -> StrataError:
    """Log and return the `UnknownReference` error for a compromised-user
    scenario naming no `runs_as` node, for
    `build_compromised_user_scenario`."""
    _log.error("scenario: compromised-user scenario for %r names no runs_as node", user)
    return StrataError.UnknownReference


# frob:doc docs/strata/host.md#movement-impossibility-proofs
# frob:tests tests/unit/strata/test_host_isolation.py::test_blast_radius kind="unit"
def build_compromised_user_scenario(
    model: KernelModel, user: str, scenario_id: str
) -> Result[Scenario, StrataError]:
    """Build the compromised-service-owner red-team `Scenario` (T-0256):
    every node declaring `runs_as=<user>` (linux) OR `service_account=
    <user>` (windows, T-0606, `_host.py::host_manifest_for`) is
    downgraded to `SetTrust(node_id, "foreign")` -- the SAME rewrite
    component compromise already uses -- and one `NoFlow(src="foreign",
    dst=<node>)` claim is asserted for EVERY node NOT in the user's
    manifest slice, so `evaluate_scenarios` re-checking this scenario
    proves (or refutes) that the compromise's blast radius is EXACTLY
    that user's own slice, no wider -- a windows `service_account`
    identity proves the identical shape of blast-radius claim a linux
    `runs_as` identity does (docs/strata/host.md#windows-wiring-t-0606).

    The rewrites ALSO include an `AddFlow` per `_host_isolation.py::
    host_movement_flows`-derived edge (module docstring's REJECT-round
    fix): without these the `NoFlow` claims above would be proved purely
    over the declared app-flow graph, blind to filesystem/OS movement
    HOST001 already detects -- the exact vacuity a review round caught.
    With them, a shared writable path or reachable socket/pipe with NO
    declared `Flow` correctly REFUTES the claim instead of vacuously
    proving it.

    Fails closed (`StrataError.UnknownReference`) when `user` names no
    `runs_as`/`service_account` declared anywhere in `model` -- zero
    rewrites would vacuously "prove" every claim, misreporting a typo'd
    user name as a genuine isolation proof (charter law 2, deny-by-default)."""
    user_nodes = _compromised_user_nodes(model, user)
    if not user_nodes:
        return Err(_no_runs_as_error(user))
    return Ok(_build_blast_radius_scenario(model, user, user_nodes, scenario_id))


def _build_blast_radius_scenario(
    model: KernelModel, user: str, user_nodes: list[str], scenario_id: str
) -> Scenario:
    """Assemble and log the built `Scenario` from the compromised slice,
    split out of `build_compromised_user_scenario` purely to keep that
    function's body short."""
    movement_rewrites, rewrites = _blast_radius_rewrites(model, user_nodes)
    claims = _blast_radius_claims(model, user, user_nodes)
    _log.info(
        "scenario: built compromised-user scenario %s for %r (%d node(s) "
        "compromised, %d movement flow(s), %d blast-radius claim(s))",
        scenario_id,
        user,
        len(user_nodes),
        len(movement_rewrites),
        len(claims),
    )
    return Scenario(id=scenario_id, rewrites=rewrites, claims=claims)


def _compromised_user_nodes(model: KernelModel, user: str) -> list[str]:
    """Every node id whose `runs_as` (linux) or `service_account`
    (windows, T-0606) matches `user` (`_host.py::host_manifest_for`),
    sorted -- the compromised slice for
    `build_compromised_user_scenario`."""
    return sorted(
        node.id
        for node in model.nodes
        if (manifest := host_manifest_for(node)) is not None
        and (manifest.runs_as == user or manifest.service_account == user)
    )


def _blast_radius_rewrites(
    model: KernelModel, user_nodes: list[str]
) -> tuple[tuple[Rewrite, ...], tuple[Rewrite, ...]]:
    """The `(movement_rewrites, all_rewrites)` pair for
    `build_compromised_user_scenario`: movement `AddFlow`s
    (`_host_isolation.py::host_movement_flows`) plus a `SetTrust` per
    compromised node."""
    movement_rewrites: tuple[Rewrite, ...] = tuple(
        AddFlow(flow=flow) for flow in host_movement_flows(model)
    )
    trust_rewrites: tuple[Rewrite, ...] = tuple(
        SetTrust(node_id=node_id, level=_COMPROMISED_TRUST) for node_id in user_nodes
    )
    return movement_rewrites, movement_rewrites + trust_rewrites


def _blast_radius_claims(
    model: KernelModel, user: str, user_nodes: list[str]
) -> tuple[Claim, ...]:
    """One `NoFlow` blast-radius `Claim` per node outside the compromised
    slice, for `build_compromised_user_scenario`."""
    outside = sorted(node.id for node in model.nodes if node.id not in user_nodes)
    return tuple(
        Claim(
            id=f"blast-radius:{user}:{node_id}",
            body=NoFlow(src=_COMPROMISED_TRUST, dst=node_id),
        )
        for node_id in outside
    )


def _no_krb_node_error(node_id: str) -> StrataError:
    """Log and return the `UnknownReference` error for a compromised-krb
    scenario naming no declared node, for
    `build_compromised_krb_scenario`."""
    _log.error("scenario: compromised-krb scenario names undeclared node %r", node_id)
    return StrataError.UnknownReference


# frob:doc docs/strata/krb.md#movement-proofs
# frob:tests tests/unit/strata/test_krb_movement.py::TestKrbScen.test_all kind="unit"
def build_compromised_krb_scenario(
    model: KernelModel, node_id: str, scenario_id: str
) -> Result[Scenario, StrataError]:
    """Build the compromised-krb-principal red-team `Scenario` (T-0263,
    reusing the T-0073 scenario engine `build_compromised_user_scenario`
    already reuses for HOST001/HOST002, T-0256): `node_id` is downgraded
    via `SetTrust(node_id, "foreign")`, plus one `AddFlow` per edge
    `_krb_delegation_movement_flows` derives from its declared
    `delegation` -- unconstrained delegation materializes an edge to
    EVERY other node (the true worst-case reach KRB001 names: it can
    impersonate ANY user to ANY service), constrained delegation
    materializes edges only to its resolved `target` SPNs' owning nodes.
    One `NoFlow(src="foreign", dst=<node>)` claim is asserted per node
    OUTSIDE that reach set, so `evaluate_scenarios` re-checking this
    scenario proves (or refutes) the compromise's blast radius is
    bounded by exactly what the node's own delegation grants -- refuted
    the moment the closure actually reaches further, never vacuously
    proved over an unrelated declared-flow graph (the T-0256 review-round
    failure `_host_isolation.py`'s module docstring records, guarded
    against here the same way).

    Fails closed (`StrataError.UnknownReference`) when `node_id` names no
    node in `model` at all -- zero rewrites would vacuously "prove" every
    claim, misreporting a typo'd node id as a genuine isolation proof
    (charter law 2, deny-by-default)."""
    known_ids = {n.id for n in model.nodes}
    if node_id not in known_ids:
        return Err(_no_krb_node_error(node_id))
    movement_flows = _krb_delegation_movement_flows(model, node_id)
    rewrites: tuple[Rewrite, ...] = (
        *(AddFlow(flow=flow) for flow in movement_flows),
        SetTrust(node_id=node_id, level=_COMPROMISED_TRUST),
    )
    outside = sorted(n.id for n in model.nodes if n.id != node_id)
    claims = tuple(
        Claim(
            id=f"krb-blast-radius:{node_id}:{other_id}",
            body=NoFlow(src=_COMPROMISED_TRUST, dst=other_id),
        )
        for other_id in outside
    )
    _log.info(
        "scenario: built compromised-krb scenario %s for %r (%d movement "
        "flow(s), %d blast-radius claim(s))",
        scenario_id,
        node_id,
        len(movement_flows),
        len(claims),
    )
    return Ok(Scenario(id=scenario_id, rewrites=rewrites, claims=claims))


def _krb_delegation_movement_flows(
    model: KernelModel, node_id: str
) -> tuple[Flow, ...]:
    """The synthetic `Flow`s `build_compromised_krb_scenario` adds for
    one compromised krb-bound node, derived purely from its OWN declared
    `delegation` (module docstring's per-kind reach)."""
    node = next((n for n in model.nodes if n.id == node_id), None)
    if node is None:
        return ()
    manifest = krb_manifest_for(node)
    if manifest is None or manifest.delegation is None:
        return ()
    if manifest.delegation == KrbDelegationKind.UNCONSTRAINED:
        return tuple(
            Flow(
                id=f"krb-movement:{node_id}->{other.id}",
                src=node_id,
                dst=other.id,
                attrs=("krb_movement=unconstrained",),
            )
            for other in model.nodes
            if other.id != node_id
        )
    if manifest.delegation == KrbDelegationKind.CONSTRAINED:
        spn_owner: dict[str, str] = {}
        for other in model.nodes:
            other_manifest = krb_manifest_for(other)
            if other_manifest is None:
                continue
            for spn in other_manifest.spns:
                spn_owner.setdefault(spn, other.id)
        targets = sorted(
            {
                spn_owner[target_spn]
                for target_spn in manifest.delegation_targets
                if target_spn in spn_owner and spn_owner[target_spn] != node_id
            }
        )
        return tuple(
            Flow(
                id=f"krb-movement:{node_id}->{target}",
                src=node_id,
                dst=target,
                attrs=("krb_movement=constrained",),
            )
            for target in targets
        )
    return ()
