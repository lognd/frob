"""Atomic/saga contracts for the strata kernel
(docs/strata/boundary.md#frames-and-failure-atomicity, T-0075).

Two joined checks over an `operation`'s `modifies {} on Err` strong
guarantee (T-0069's `CrossStoreAtomicity` refusal already gates parsing
into a `KernelModel` -- an illegitimate cross-store claim never reaches
this module):

1. **Saga retry-idempotency join.** An operation that legitimately spans
   stores does so only via a declared `coordinator` node (the surviving
   escape valve past `CrossStoreAtomicity`), which `docs/strata/
   boundary.md` calls a saga: "the compensating action is retried
   (at-least-once) and therefore must be idempotent -- the standard
   delivery-semantics join applies." This module marks every flow into
   such a coordinator at-least-once and hands the model to
   `_facts.py::build_facts`, so the idempotency finding fires through the
   SAME diagnostic path used for queues and crash contracts (T-0074),
   never a parallel one that could drift.
2. **Exhaustive fault injection (L2).** From every operation declaring the
   strong guarantee (`modifies {} on Err`), one `FaultInjectionCase` per
   variant of its caller-supplied `ErrorSet` is generated mechanically
   (docs/strata/evidence.md#exhaustive-fault-injection-l2-with-teeth) --
   complete over the declared error model, categorically stronger than
   sampled property testing. v0's surface grammar has no construct tying
   an `operation` to the Python `ErrorSet` its fallible dependency raises
   (the same class of grammar gap T-0074 deferred to T-0118), so callers
   supply that mapping directly; an operation absent from the mapping
   generates no cases rather than failing closed, since "no ErrorSet
   declared" is a coverage gap to surface elsewhere, not a structural
   fault in this model.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import Module
from ._elaborate import _COORDINATOR_ATTR
from ._errors import StrataError
from ._facts import build_facts
from ._models import _AT_LEAST_ONCE, KernelModel

_log = get_logger(__name__)


# frob:doc docs/strata/evidence.md#exhaustive-fault-injection-l2-with-teeth
class FaultInjectionCase(BaseModel):
    """One generated exhaustive-fault-injection test case for an atomic operation."""

    model_config = ConfigDict(frozen=True)

    id: str
    operation_id: str
    error_variant: str
    assertion: str


# frob:doc docs/strata/boundary.md#frames-and-failure-atomicity
class AtomicContractReport(BaseModel):
    """The joined output of saga idempotency diagnostics and generated fault cases."""

    model_config = ConfigDict(frozen=True)

    saga_diagnostics: tuple[str, ...]
    fault_injection_cases: tuple[FaultInjectionCase, ...]


def _saga_coordinator_ids(module: Module) -> frozenset[str]:
    """Coordinator node ids actually serving as a legitimate cross-store saga.

    An operation reaches this point only after elaboration's
    `CrossStoreAtomicity` refusal has already passed (`_elaborate.py::
    _validate_operations`), so any surviving `atomic_via` that differs
    from `on` and names a `coordinator`-attr node is, by construction, a
    declared saga -- never re-derives the refusal logic, only identifies
    which coordinators it let through.
    """
    coordinator_node_ids = {n.id for n in module.nodes if _COORDINATOR_ATTR in n.attrs}
    return frozenset(
        op.atomic_via
        for op in module.operations
        if not op.modifies_err
        and op.atomic_via != op.on
        and op.atomic_via in coordinator_node_ids
    )


def _join_saga_idempotency(
    model: KernelModel, coordinator_ids: frozenset[str]
) -> KernelModel:
    """Mark every flow into a saga coordinator at-least-once.

    WHY: a saga's compensating action is retried, which demands idempotent
    effects downstream (docs/strata/boundary.md). This injects exactly the
    attr `_facts.py::_structural_diagnostics` already looks for -- the
    identical mechanism `_crash.py::_join_retry_idempotency` uses for
    crash-retry, reused rather than duplicated. Never mutates `model`;
    returns a copy.
    """
    if not coordinator_ids:
        return model
    flows = list(model.flows)
    for i, flow in enumerate(flows):
        if flow.dst in coordinator_ids and _AT_LEAST_ONCE not in flow.attrs:
            _log.info(
                "saga join: flow %s into coordinator %s treated as "
                "at-least-once (T-0075)",
                flow.id,
                flow.dst,
            )
            flows[i] = flow.model_copy(update={"attrs": (*flow.attrs, _AT_LEAST_ONCE)})
    return model.model_copy(update={"flows": tuple(flows)})


# frob:doc docs/strata/boundary.md#frames-and-failure-atomicity
def evaluate_saga_contracts(
    module: Module, model: KernelModel
) -> Result[tuple[str, ...], StrataError]:
    """Join every declared saga's retry-idempotency obligation into `FactBase`.

    A model with no saga coordinators returns an empty diagnostics tuple
    rather than an error -- sagas are opt-in, implied only by a
    `CrossStoreAtomicity`-surviving `atomic_via` (docs/strata/boundary.md
    #frames-and-failure-atomicity, T-0075).
    """
    coordinator_ids = _saga_coordinator_ids(module)
    if not coordinator_ids:
        _log.info("evaluate_saga_contracts: no saga coordinators declared")
        return Ok(())
    joined = _join_saga_idempotency(model, coordinator_ids)
    facts = build_facts(joined)
    if facts.is_err:
        return Err(facts.danger_err)
    _log.info(
        "evaluated %d saga coordinator(s): %d diagnostic(s)",
        len(coordinator_ids),
        len(facts.danger_ok.diagnostics),
    )
    return Ok(facts.danger_ok.diagnostics)


# frob:doc docs/strata/evidence.md#exhaustive-fault-injection-l2-with-teeth
def generate_fault_injection_cases(
    module: Module, error_sets: Mapping[str, type[ErrorSet]]
) -> tuple[FaultInjectionCase, ...]:
    """One `FaultInjectionCase` per `ErrorSet` variant, for every strong-guarantee op.

    Only operations declaring `modifies {} on Err` (the empty-err-frame
    strong guarantee) are eligible -- a nonempty `on Err` frame already
    documents its own effects and is not the atomicity claim this
    generation targets (docs/strata/boundary.md#frames-and-failure
    -atomicity). `error_sets` maps operation id to the Python `ErrorSet`
    its fallible dependency raises; an eligible operation absent from the
    mapping is logged and skipped, not failed closed -- v0's surface
    grammar has no construct declaring that link yet (T-0118-class gap).
    Variant order follows the `ErrorSet`'s own declaration order (already
    deterministic), never re-sorted.
    """
    cases: list[FaultInjectionCase] = []
    for op in module.operations:
        if op.modifies_err:
            continue
        error_set = error_sets.get(op.id)
        if error_set is None:
            _log.info(
                "operation %s: no ErrorSet declared for fault-injection "
                "generation (surface grammar gap, T-0118)",
                op.id,
            )
            continue
        for variant in error_set:
            cases.append(
                FaultInjectionCase(
                    id=f"{op.id}__fault_{variant.name}",
                    operation_id=op.id,
                    error_variant=variant.name,
                    assertion=(
                        f"state digest unchanged when {op.on} raises "
                        f"{error_set.__name__}.{variant.name}"
                    ),
                )
            )
    _log.info("generated %d fault-injection case(s)", len(cases))
    return tuple(cases)


# frob:doc docs/strata/boundary.md#frames-and-failure-atomicity
# frob:waive TEST005 reason="evaluate_atomic_contracts 83.3% branch cover, debt T-0160"
def evaluate_atomic_contracts(
    module: Module,
    model: KernelModel,
    *,
    error_sets: Mapping[str, type[ErrorSet]] | None = None,
) -> Result[AtomicContractReport, StrataError]:
    """Validate saga idempotency and generate fault-injection cases for `module`.

    The single entry point joining both T-0075 checks (module docstring);
    `error_sets` defaults to empty, which is a valid input (no cases
    generated, never an error) since not every operation need declare
    fault injection in v0.
    """
    saga = evaluate_saga_contracts(module, model)
    if saga.is_err:
        return Err(saga.danger_err)
    cases = generate_fault_injection_cases(module, error_sets or {})
    return Ok(
        AtomicContractReport(
            saga_diagnostics=saga.danger_ok, fault_injection_cases=cases
        )
    )
