"""Crash contracts for the strata kernel
(docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims).

A node's `on crash { restart within t; inflight fail retriable within t';
state recovered from X }` contract desugars to three joined checks
(T-0074):

1. **Auto-generated crash scenario.** "Crash" is modeled as total node
   loss -- the existing `RemoveNode` scenario rewrite -- with every
   declared claim re-checked under it. This module builds the `Scenario`
   and hands it to `_scenarios.py::evaluate_scenarios`; it never
   duplicates rewrite or claim-evaluation logic.
2. **The no-hang check.** Every synchronous flow into a crashable node
   must declare a `timeout` at least as long as the contract's
   restart+retry bound, else the model fails closed -- a caller with no
   timeout (or one shorter than the recovery window) blocks forever on
   exactly the failure class this contract exists to bound.
3. **The crash-retry-idempotency join.** A contract with a `retry` bound
   means inflight requests are retried on crash, which is at-least-once
   delivery by definition. Every inbound flow is marked at-least-once so
   the existing queue-delivery join in `_facts.py` (dst must carry
   `idempotent`) fires through the SAME diagnostic path used for queues,
   rather than a parallel one that could drift.
"""

from __future__ import annotations

import datetime as _dt

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import build_facts
from ._models import (
    _AT_LEAST_ONCE,
    CrashContract,
    Flow,
    KernelModel,
    Node,
    RemoveNode,
    Scenario,
)
from ._policy import CompiledPolicies
from ._scenarios import ScenarioResult, evaluate_scenarios

_log = get_logger(__name__)

#: Flow attr exempting a caller from the no-hang check (e.g. a queue
#: consumer, whose recovery window is governed by delivery semantics
#: rather than a synchronous wait).
_ASYNC_ATTR = "async"


# frob:doc docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims
class CrashContractReport(BaseModel):
    """The joined output of crash-scenario claims plus retry-idempotency diagnostics."""

    model_config = ConfigDict(frozen=True)

    scenario_results: tuple[ScenarioResult, ...]
    diagnostics: tuple[str, ...]


def _crash_bound_seconds(contract: CrashContract) -> Result[float, StrataError]:
    """`restart` + `retry` (retry defaults to 0) converted to base-unit seconds."""
    restart_base = contract.restart.base_value()
    if restart_base.is_err:
        return Err(restart_base.danger_err)
    total = restart_base.danger_ok
    if contract.retry is not None:
        retry_base = contract.retry.base_value()
        if retry_base.is_err:
            return Err(retry_base.danger_err)
        total += retry_base.danger_ok
    return Ok(total)


def _validate_recovery_sources(
    model: KernelModel, crashable: dict[str, Node]
) -> Result[None, StrataError]:
    """Every declared `recovers_from` must name a real node, else `UnknownReference`.

    Fails closed (law 2): a crash contract claiming state recovers from
    an undeclared node is a dangling promise, not a silently accepted one.
    """
    known = {n.id for n in model.nodes}
    for node in crashable.values():
        assert node.crash is not None
        target = node.crash.recovers_from
        if target is not None and target not in known:
            _log.error(
                "node %s: crash recovers_from target %r is not declared",
                node.id,
                target,
            )
            return Err(StrataError.UnknownReference)
    return Ok(None)


# frob:invariant INV-027
# frob:tests tests/unit/strata/test_crash.py::TestNoHangCheck.test_missing_timeout_into_crashable_node_fails_closed  # noqa: E501
def _validate_no_hang_flow(flow: Flow, node: Node) -> Result[None, StrataError]:
    """No-hang check body for one flow into one crashable `node`."""
    assert node.crash is not None
    bound = _crash_bound_seconds(node.crash)
    if bound.is_err:
        return Err(bound.danger_err)
    if flow.timeout is None:
        _log.error(
            "flow %s: no timeout declared calling crashable node %s "
            "(no-hang check, T-0074)",
            flow.id,
            node.id,
        )
        return Err(StrataError.MissingTimeout)
    timeout_base = flow.timeout.base_value()
    if timeout_base.is_err:
        return Err(timeout_base.danger_err)
    if timeout_base.danger_ok < bound.danger_ok:
        _log.error(
            "flow %s: timeout %s%s is shorter than crashable node %s's "
            "restart+retry bound %.3fs (no-hang check, T-0074)",
            flow.id,
            flow.timeout.value,
            flow.timeout.unit,
            node.id,
            bound.danger_ok,
        )
        return Err(StrataError.IncompatibleTimeout)
    return Ok(None)


def _validate_no_hang(
    model: KernelModel, crashable: dict[str, Node]
) -> Result[None, StrataError]:
    """Every synchronous flow into a crashable node needs a compatible timeout.

    Fails closed (law 2): a missing timeout is `MissingTimeout`; a
    declared timeout shorter than the contract's restart+retry bound is
    `IncompatibleTimeout` -- a caller that gives up before recovery can
    plausibly complete is the same silent-hang class this check exists to
    kill. Flows carrying the `async` attr are exempt (module docstring).
    """
    for flow in model.flows:
        node = crashable.get(flow.dst)
        if node is None or node.crash is None:
            continue
        if _ASYNC_ATTR in flow.attrs:
            continue
        result = _validate_no_hang_flow(flow, node)
        if result.is_err:
            return result
    return Ok(None)


def _join_retry_idempotency(
    model: KernelModel, crashable: dict[str, Node]
) -> KernelModel:
    """Mark every flow into a retry-bearing crashable node at-least-once.

    WHY: crash + retry implies at-least-once, which demands idempotent
    effects downstream (docs/strata/boundary.md). This injects exactly
    the attr `_facts.py::_structural_diagnostics` already looks for, so
    the idempotency finding is produced by the SAME code as the ordinary
    queue-delivery join rather than a duplicate check that could drift.
    Never mutates `model`; returns a copy.
    """
    retry_targets = {
        node.id
        for node in crashable.values()
        if node.crash is not None and node.crash.retry is not None
    }
    if not retry_targets:
        return model
    flows = list(model.flows)
    for i, flow in enumerate(flows):
        if flow.dst in retry_targets and _AT_LEAST_ONCE not in flow.attrs:
            _log.info(
                "crash-retry join: flow %s into %s treated as at-least-once (T-0074)",
                flow.id,
                flow.dst,
            )
            flows[i] = flow.model_copy(update={"attrs": (*flow.attrs, _AT_LEAST_ONCE)})
    return model.model_copy(update={"flows": tuple(flows)})


def _generate_crash_scenarios(
    model: KernelModel, crashable: dict[str, Node]
) -> tuple[Scenario, ...]:
    """One auto-generated node-loss scenario per crashable node, in node-id order.

    WHY: `on crash { ... }` desugars to an auto-generated crash scenario
    plus bounds (docs/strata/boundary.md) -- "crash" is total node loss,
    the existing `RemoveNode` rewrite, and every declared claim is
    re-checked under it exactly like any hand-written scenario, so this
    reuses `evaluate_scenarios` rather than a parallel evaluator.
    """
    node_ids = sorted(crashable)  # hoisted: sorted once, not per iteration
    return tuple(
        Scenario(
            id=f"{node_id}__crash",
            rewrites=(RemoveNode(node_id=node_id),),
            claims=model.claims,
        )
        for node_id in node_ids
    )


def _crash_scenario_results(
    model: KernelModel,
    crashable: dict[str, Node],
    *,
    today: _dt.date | None,
    compiled_policies: CompiledPolicies | None,
    waived_policies: frozenset[str],
) -> Result[tuple[tuple[Scenario, ...], tuple[ScenarioResult, ...]], StrataError]:
    """Generate + evaluate the auto-generated crash scenarios for `crashable`."""
    generated = _generate_crash_scenarios(model, crashable)
    scenario_model = model.model_copy(update={"scenarios": generated})
    scenarios = evaluate_scenarios(
        scenario_model,
        today=today,
        compiled_policies=compiled_policies,
        waived_policies=waived_policies,
    )
    if scenarios.is_err:
        return Err(scenarios.danger_err)
    return Ok((generated, scenarios.danger_ok))


def _crash_diagnostics(
    model: KernelModel, crashable: dict[str, Node]
) -> Result[tuple[str, ...], StrataError]:
    """Recovery-source + no-hang validation, then the retry-idempotency join's
    diagnostics -- the first three steps of `evaluate_crash_contracts`, in order."""
    recovery_ok = _validate_recovery_sources(model, crashable)
    if recovery_ok.is_err:
        return Err(recovery_ok.danger_err)
    no_hang_ok = _validate_no_hang(model, crashable)
    if no_hang_ok.is_err:
        return Err(no_hang_ok.danger_err)

    joined = _join_retry_idempotency(model, crashable)
    facts = build_facts(joined)
    if facts.is_err:
        return Err(facts.danger_err)
    return Ok(facts.danger_ok.diagnostics)


# frob:doc docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims
def evaluate_crash_contracts(
    model: KernelModel,
    *,
    today: _dt.date | None = None,
    compiled_policies: CompiledPolicies | None = None,
    waived_policies: frozenset[str] = frozenset(),
) -> Result[CrashContractReport, StrataError]:
    """Validate and evaluate every `on crash` contract declared in `model`.

    Order (all fail closed, first error wins): recovery-source references
    resolve, then the no-hang check, then the retry-idempotency join
    (surfaced as `FactBase.diagnostics`, non-fatal like the ordinary
    queue-delivery join it reuses), then the auto-generated crash
    scenarios are evaluated via `evaluate_scenarios`. A model with no
    crash contracts returns an empty report rather than an error -- crash
    contracts are opt-in, not implied by every node (docs/strata/
    boundary.md#crash-contracts-and-error-totality-adjacent-claims, T-0074).
    """
    crashable = {n.id: n for n in model.nodes if n.crash is not None}
    if not crashable:
        _log.info("evaluate_crash_contracts: no crash contracts declared")
        return Ok(CrashContractReport(scenario_results=(), diagnostics=()))
    return _evaluate_crashable_contracts(
        model,
        crashable,
        today=today,
        compiled_policies=compiled_policies,
        waived_policies=waived_policies,
    )


def _evaluate_crashable_contracts(
    model: KernelModel,
    crashable: dict[str, Node],
    *,
    today: _dt.date | None,
    compiled_policies: CompiledPolicies | None,
    waived_policies: frozenset[str],
) -> Result[CrashContractReport, StrataError]:
    """The non-empty-`crashable` path of `evaluate_crash_contracts`: run the
    diagnostics steps, then the scenario evaluation, then assemble the report."""
    diagnostics_out = _crash_diagnostics(model, crashable)
    if diagnostics_out.is_err:
        return Err(diagnostics_out.danger_err)
    diagnostics = diagnostics_out.danger_ok

    scenario_out = _crash_scenario_results(
        model,
        crashable,
        today=today,
        compiled_policies=compiled_policies,
        waived_policies=waived_policies,
    )
    if scenario_out.is_err:
        return Err(scenario_out.danger_err)
    generated, scenario_results = scenario_out.danger_ok
    return Ok(_build_crash_report(crashable, generated, scenario_results, diagnostics))


def _build_crash_report(
    crashable: dict[str, Node],
    generated: tuple[Scenario, ...],
    scenario_results: tuple[ScenarioResult, ...],
    diagnostics: tuple[str, ...],
) -> CrashContractReport:
    """Log the final crash-contract counts and assemble the report."""
    _log.info(
        "evaluated %d crash contract(s): %d scenario(s), %d diagnostic(s)",
        len(crashable),
        len(generated),
        len(diagnostics),
    )
    return CrashContractReport(
        scenario_results=scenario_results, diagnostics=diagnostics
    )
