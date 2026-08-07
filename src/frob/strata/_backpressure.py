"""REL26x reliability family: BACKPRESSURE bounded-intake obligation on
queue/consumer nodes (T-0646, child of the T-0331 systems-checks epic,
docs/strata/reliability.md), mirroring `_circuit_breaker.py`'s REL23x
structure (module docstring precedent, T-0699/T-0640/.../T-0645: one rule
module per obligation, same `Report`/`Violation` pydantic pair,
registration/exemption from `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
CLI wiring via `frob.app.sys_runner`). Extends `_lint.py`'s LINT003
surge/LINT005 capacity ideas (module docstring, T-0646 ticket body) to a
NEW population: a queue or consumer node needs its OWN declared bounded-
intake policy (backpressure), not just a capacity headroom claim -- an
unbounded queue with infinite intake is an OOM/latency-collapse risk
regardless of what downstream capacity is declared.

TWO RULES, both NODE-scoped (a node has at most one `queue`/`consumer`
marker pairing and fires at most one REL260/REL261 finding each --
single-instance-per-node, the same carve-out `_circuit_breaker.py`'s
REL230/REL231 pair already establishes, NOT registered in
`MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL260 missing bounded intake: a node marked `queue` or `consumer`
    (this node buffers or drains work -- a message queue, a worker pool
    consumer, anything that can receive faster than it can drain) with no
    `bounded_intake` attr declared. Deny-by-default: an unbounded queue
    accepts intake without limit, so a slow/failed consumer becomes an
    unbounded memory/latency liability instead of a bounded, observable
    one.
  - REL261 unproven bounded intake: a node DOES declare `bounded_intake`,
    but the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- the node must have at least one file bound to it
    (`_obligation_proof.py::node_has_bound_code`) containing a real
    bounded-queue/backpressure-shaped token. A node with no bound code at
    all is UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/
    REL231 draw.

GRAMMAR-DATA CEILING, HONESTLY: `queue`/`consumer`/`bounded_intake` are
all bare Node attrs (no numeric magnitude -- the same digit-led-literal
ceiling `strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause
imposes on every other REL2xx marker), so REL260/REL261 prove PRESENCE of
a declared bounded-intake obligation and its code-level evidence, not a
specific queue depth or drop policy. No `strata-core` change needed (this
ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/T-0641/T-0642's).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import files_evidence_token, node_has_bound_code, owner_index
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL260 missing bounded intake: a
#: `queue`/`consumer` node with no `bounded_intake` attr declared.
# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
REL_MISSING_BOUNDED_INTAKE = "REL260"

#: `frob sys audit` rule id for REL261 unproven bounded intake: a node
#: declares `bounded_intake`, but its bound code has no real bounded-
#: queue/backpressure-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
REL_UNPROVEN_BOUNDED_INTAKE = "REL261"

#: Every REL26x rule id this module can emit -- this module's own, narrow
#: family for `_apply_backpressure_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
BACKPRESSURE_RULES: frozenset[str] = frozenset(
    {REL_MISSING_BOUNDED_INTAKE, REL_UNPROVEN_BOUNDED_INTAKE}
)

#: Node attr marking a message/work queue -- one half of the REL260/REL261
#: population (module docstring).
_QUEUE_ATTR = "queue"

#: Node attr marking a queue/stream consumer -- the other half of the
#: REL260/REL261 population (module docstring).
_CONSUMER_ATTR = "consumer"

#: Node attr discharging the REL260 bounded-intake obligation (presence-
#: only, module docstring's grammar-data ceiling).
_BOUNDED_INTAKE_ATTR = "bounded_intake"

#: Regex proving a real bounded-queue/backpressure-shaped token in bound
#: source text (REL261) -- deliberately narrow (a syntactic token scan,
#: not a semantic call-argument binding), matching common bounded-queue/
#: backpressure-library shapes: a `maxsize=`/`max_size=` kwarg, a
#: `Semaphore(`/`BoundedSemaphore(` construct, or a literal `backpressure`/
#: `bounded_queue`/`token_bucket`/`rate_limit` identifier. Same honesty
#: line `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token bounds the SAME queue the
#: node models, only that the node's bound code contains real evidence of
#: a bounded-intake construct.
_BOUNDED_INTAKE_TOKEN_RE = re.compile(
    r"(max(?:_?)size\s*=|BoundedSemaphore\(|\bSemaphore\(|\bbackpressure\b|"
    r"bounded_queue|token_bucket|rate_limit)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
class BackpressureViolation(BaseModel):
    """One REL26x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one REL260/REL261 finding each), the same bare-rule
    waiver carve-out REL230/REL231 use. Mirrors
    `_circuit_breaker.py::CircuitBreakerViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
class BackpressureReport(BaseModel):
    """Every UNWAIVED REL26x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_circuit_breaker.py::CircuitBreakerReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[BackpressureViolation, ...] = ()
    waived: tuple[BackpressureViolation, ...] = ()


def _is_queue_or_consumer(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `queue` or `consumer` marker
    -- the REL260/REL261 population (module docstring)."""
    return _QUEUE_ATTR in attrs or _CONSUMER_ATTR in attrs


def _has_bounded_intake(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `bounded_intake` marker."""
    return _BOUNDED_INTAKE_ATTR in attrs


def _missing_bounded_intake_violations(
    model: KernelModel,
) -> list[BackpressureViolation]:
    """REL260: every `queue`/`consumer` node with no `bounded_intake` attr."""
    violations: list[BackpressureViolation] = []
    for node in model.nodes:
        if not _is_queue_or_consumer(node.attrs) or _has_bounded_intake(node.attrs):
            continue
        _log.warning(
            "backpressure: REL260 node %s is queue/consumer with no bounded "
            "intake policy",
            node.id,
        )
        violations.append(
            BackpressureViolation(
                rule=REL_MISSING_BOUNDED_INTAKE,
                node=node.id,
                detail=(
                    f"node {node.id} is a queue/consumer with no bounded-intake "
                    "obligation (no `bounded_intake` attr)"
                ),
            )
        )
    return violations


def _unproven_bounded_intake_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[BackpressureViolation]:
    """REL261: every `queue`/`consumer` node declaring `bounded_intake`
    with bound code, but whose bound code carries no real bounded-queue/
    backpressure-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_circuit_breaker.py::_unproven_circuit_breaker_violations` exactly,
    parameterized on `_BOUNDED_INTAKE_TOKEN_RE`."""
    violations: list[BackpressureViolation] = []
    for node in model.nodes:
        if not _is_queue_or_consumer(node.attrs) or not _has_bounded_intake(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _BOUNDED_INTAKE_TOKEN_RE):
            continue
        _log.warning(
            "backpressure: REL261 node %s declares bounded_intake but bound "
            "code has no real bounded-intake token",
            node.id,
        )
        violations.append(
            BackpressureViolation(
                rule=REL_UNPROVEN_BOUNDED_INTAKE,
                node=node.id,
                detail=(
                    f"node {node.id} declares bounded_intake, but its bound "
                    "code has no real bounded-queue/backpressure token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_backpressure_waivers(
    model: KernelModel, violations: list[BackpressureViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_circuit_breaker.py::_apply_circuit_breaker_waivers`'s pattern reused
    for the REL26x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in BACKPRESSURE_RULES,
    )


# frob:doc docs/strata/reliability.md#rel26x-backpressure-obligation-t-0646
# frob:ticket T-0646
# frob:ticket T-0958
# frob:enforces SDC-5-LOAD-SHEDDING
# frob:enforces CHK-GATE-REL260
# frob:enforces CHK-GATE-REL261
# frob:tests tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake.test_queue_node_without_bounded_intake_fires  # noqa: E501
def check_backpressure_obligations(
    model: KernelModel, root: Path
) -> Result[BackpressureReport, StrataError]:
    """The REL26x BACKPRESSURE-obligation entrypoint (T-0646): REL260
    (missing bounded intake) and REL261 (declared-but-unproven bounded
    intake, proof-against-code) across every queue/consumer node in
    `model`, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_circuit_breaker_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[BackpressureViolation] = []
    violations.extend(_missing_bounded_intake_violations(model))
    violations.extend(_unproven_bounded_intake_violations(model, owner_by_node, root))
    applied = _apply_backpressure_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        BackpressureViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
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
        "backpressure: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(BackpressureReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "BACKPRESSURE_RULES",
    "REL_MISSING_BOUNDED_INTAKE",
    "REL_UNPROVEN_BOUNDED_INTAKE",
    "BackpressureReport",
    "BackpressureViolation",
    "check_backpressure_obligations",
]
