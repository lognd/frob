"""REL23x reliability family: CIRCUIT BREAKER / bulkhead obligation per
external dependency (T-0642, child of the T-0331 systems-checks epic,
docs/strata/reliability.md), mirroring `_reliability.py`'s REL2xx TIMEOUT
structure and `_retry.py`'s REL22x RETRY structure (module docstring
precedent, T-0699/T-0640/T-0641: one rule module per obligation, same
`Report`/`Violation` pydantic pair, registration/exemption from
`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, CLI wiring via
`frob.app.sys_runner`). Extends `_lint.py`'s LINT004 kill-switch idea
(a risky capability needs an operator escape hatch) to a NEW population:
every node this model marks as an external dependency needs its OWN
escape hatch against that dependency's failure -- a circuit breaker/
bulkhead policy, not a kill-switch on the node's own capability.

TWO RULES, both NODE-scoped (a node has at most one `external` marker and
fires at most one REL230/REL231 finding each -- single-instance-per-node,
the same carve-out `_reliability.py`'s REL210/REL211 HEALTH pair already
establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL230 missing circuit breaker/bulkhead: a node marked `external`
    (this node models a real external dependency -- a third-party
    service, a foreign registry, anything outside this system's own
    blast radius) with no `circuit_breaker` attr declared. Deny-by-
    default: an unguarded call into an external dependency risks
    cascading failure the moment that dependency degrades.
  - REL231 unproven circuit breaker: a node DOES declare
    `circuit_breaker`, but the T-0331 PROVABILITY CONSTRAINT forbids
    discharging it by bare declaration alone -- the node must have at
    least one file bound to it (`_obligation_proof.py::
    node_has_bound_code`) containing a real circuit-breaker/bulkhead-
    shaped token. A node with no bound code at all is UNCHECKABLE, not
    unproven -- the same ceiling REL201/REL222 draw.

`_CRITICAL_ATTR` (the `critical` bare marker) is ALSO defined here rather
than in `_fallback.py`: T-0643 (FALLBACK, blocked_by this ticket) reuses
this exact dependency-criticality classification per its own ticket body
("Reuses the circuit-breaker ticket's dependency-criticality
classification, hence blocked on that groundwork existing") -- one home
for the marker, imported by `_fallback.py` rather than each module
defining its own copy (charter: no duplication; unlike `_IDEMPOTENT_ATTR`
in `_retry.py`, which stays a deliberate local copy of a DIFFERENT
module's private constant for import-isolation reasons, this is the
SAME concept two sibling REL2xx modules in this same ticket family both
need, so it gets one shared home instead).

GRAMMAR-DATA CEILING, HONESTLY: `external`/`circuit_breaker`/`critical`
are all bare Node attrs (no numeric magnitude -- the same digit-led-
literal ceiling `strata-core/src/parse.rs`'s generic `attr KEY=VALUE`
clause imposes on every other REL2xx marker), so REL230/REL231 prove
PRESENCE of a declared circuit-breaker/bulkhead obligation and its
code-level evidence, not a specific failure threshold or half-open
timing. No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/T-0641's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose mirroring _reliability.py's own \
# identical waiver for the identical reason (module docstring precedent, T-0642), not \
# a separate cross-module contract"

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

#: `frob sys audit` rule id for REL230 missing circuit breaker/bulkhead: an
#: `external` node with no `circuit_breaker` attr declared.
# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
REL_MISSING_CIRCUIT_BREAKER = "REL230"

#: `frob sys audit` rule id for REL231 unproven circuit breaker: a node
#: declares `circuit_breaker`, but its bound code has no real circuit-
#: breaker/bulkhead-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
REL_UNPROVEN_CIRCUIT_BREAKER = "REL231"

#: Every REL23x rule id this module can emit -- this module's own, narrow
#: family for `_apply_circuit_breaker_waivers`' `in_scope` (the same
#: "never a shared superset" discipline `_reliability.py`'s module
#: docstring documents the real regression for).
# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
CIRCUIT_BREAKER_RULES: frozenset[str] = frozenset(
    {REL_MISSING_CIRCUIT_BREAKER, REL_UNPROVEN_CIRCUIT_BREAKER}
)

#: Node attr marking a real external dependency (third-party service,
#: foreign registry, anything outside this system's own blast radius) --
#: the population REL230/REL231 apply to.
_EXTERNAL_ATTR = "external"

#: Node attr discharging the REL230 circuit-breaker/bulkhead obligation
#: (presence-only, module docstring's grammar-data ceiling).
_CIRCUIT_BREAKER_ATTR = "circuit_breaker"

#: Node attr marking a dependency as CRITICAL -- shared with `_fallback.py`
#: (T-0643, module docstring: one home for the marker both REL2xx modules
#: in this ticket family need).
# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
CRITICAL_ATTR = "critical"

#: Regex proving a real circuit-breaker/bulkhead-shaped token in bound
#: source text (REL231) -- deliberately narrow (a syntactic token scan,
#: not a semantic call-argument binding), matching common circuit-
#: breaker-library/bulkhead shapes: a `circuit_breaker`/`circuitbreaker`
#: identifier, the `pybreaker` library, a `CircuitBreaker(` constructor
#: call, or a `bulkhead`/`Bulkhead(` isolation-pool construct. Same
#: honesty line `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token guards the SAME call the
#: node models, only that the node's bound code contains real evidence of
#: a circuit-breaker/bulkhead construct.
_CIRCUIT_BREAKER_TOKEN_RE = re.compile(
    r"(circuit.?breaker|pybreaker|CircuitBreaker\(|\bbulkhead\b|Bulkhead\()",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
class CircuitBreakerViolation(BaseModel):
    """One REL23x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one `external` marker, at most one REL230/REL231
    finding each), the same bare-rule waiver carve-out REL210/REL211 use.
    Mirrors `_reliability.py::ReliabilityViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
class CircuitBreakerReport(BaseModel):
    """Every UNWAIVED REL23x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_reliability.py::ReliabilityReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[CircuitBreakerViolation, ...] = ()
    waived: tuple[CircuitBreakerViolation, ...] = ()


# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
# frob:ticket T-0642
# frob:tests tests/unit/strata/test_circuit_breaker.py::TestPredicates.test_is_external_dependency  # noqa: E501
def is_external_dependency(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `external` marker --
    exported so `_fallback.py` (T-0643) can identify the same population
    without re-deriving the predicate."""
    return _EXTERNAL_ATTR in attrs


# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
# frob:ticket T-0642
# frob:tests tests/unit/strata/test_circuit_breaker.py::TestPredicates.test_is_critical_dependency  # noqa: E501
def is_critical_dependency(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `critical` marker --
    exported so `_fallback.py` (T-0643) reuses this exact dependency-
    criticality classification (module docstring: one home for the
    marker, blocked_by discipline)."""
    return CRITICAL_ATTR in attrs


def _has_circuit_breaker(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `circuit_breaker` marker."""
    return _CIRCUIT_BREAKER_ATTR in attrs


def _missing_circuit_breaker_violations(
    model: KernelModel,
) -> list[CircuitBreakerViolation]:
    """REL230: every `external` node with no `circuit_breaker` attr."""
    violations: list[CircuitBreakerViolation] = []
    for node in model.nodes:
        if not is_external_dependency(node.attrs) or _has_circuit_breaker(node.attrs):
            continue
        _log.warning(
            "circuit_breaker: REL230 node %s is an external dependency with "
            "no circuit-breaker/bulkhead policy",
            node.id,
        )
        violations.append(
            CircuitBreakerViolation(
                rule=REL_MISSING_CIRCUIT_BREAKER,
                node=node.id,
                detail=(
                    f"node {node.id} is marked external with no circuit-breaker/"
                    "bulkhead obligation (no `circuit_breaker` attr)"
                ),
            )
        )
    return violations


def _unproven_circuit_breaker_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[CircuitBreakerViolation]:
    """REL231: every node declaring `circuit_breaker` with bound code but
    no real circuit-breaker/bulkhead-shaped token in it (PROVABILITY
    CONSTRAINT). A node with no bound code at all is skipped -- uncheckable,
    not unproven (module docstring, same ceiling REL201/REL222 draw)."""
    violations: list[CircuitBreakerViolation] = []
    for node in model.nodes:
        if not _has_circuit_breaker(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(
            owner_by_node[node.id], root, _CIRCUIT_BREAKER_TOKEN_RE
        ):
            continue
        _log.warning(
            "circuit_breaker: REL231 node %s declares circuit_breaker but its "
            "bound code has no real circuit-breaker/bulkhead token",
            node.id,
        )
        violations.append(
            CircuitBreakerViolation(
                rule=REL_UNPROVEN_CIRCUIT_BREAKER,
                node=node.id,
                detail=(
                    f"node {node.id} declares circuit_breaker, but its bound "
                    "code has no real circuit-breaker/bulkhead token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_circuit_breaker_waivers(
    model: KernelModel, violations: list[CircuitBreakerViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_reliability.py::_apply_reliability_waivers`'s pattern reused for the
    REL23x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in CIRCUIT_BREAKER_RULES,
    )


# frob:doc docs/strata/reliability.md#rel23x-circuit-breaker--bulkhead-obligation-t-0642
# frob:ticket T-0642
# frob:tests tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker.test_external_node_without_circuit_breaker_fires  # noqa: E501
def check_circuit_breaker_obligations(
    model: KernelModel, root: Path
) -> Result[CircuitBreakerReport, StrataError]:
    """The REL23x CIRCUIT-BREAKER-obligation entrypoint (T-0642): REL230
    (missing circuit breaker/bulkhead) and REL231 (declared-but-unproven,
    proof-against-code) across every `external` node in `model`, waivers
    already applied. `root` is the repo root `_code_binding.py::bind_code`
    binds against -- `Err` propagates `bind_code`'s `AmbiguousCodeBinding`
    unchanged (deny by default, the same discipline
    `check_reliability_timeouts` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[CircuitBreakerViolation] = []
    violations.extend(_missing_circuit_breaker_violations(model))
    violations.extend(_unproven_circuit_breaker_violations(model, owner_by_node, root))
    applied = _apply_circuit_breaker_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        CircuitBreakerViolation(
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
        "circuit_breaker: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        CircuitBreakerReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "CIRCUIT_BREAKER_RULES",
    "CRITICAL_ATTR",
    "REL_MISSING_CIRCUIT_BREAKER",
    "REL_UNPROVEN_CIRCUIT_BREAKER",
    "CircuitBreakerReport",
    "CircuitBreakerViolation",
    "check_circuit_breaker_obligations",
    "is_critical_dependency",
    "is_external_dependency",
]
