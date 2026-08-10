"""REL28x reliability family: golden-signal SLO + error-budget obligation
per service (T-0648, child of the T-0331 systems-checks epic, docs/
strata/reliability.md), mirroring `_reliability.py`'s REL21x HEALTH
structure (module docstring precedent, T-0699/T-0640/.../T-0647: one rule
module per obligation, same `Report`/`Violation` pydantic pair, node-
scoped single-instance carve-out, CLI wiring via `frob.app.sys_runner`).

TWO RULES, both NODE-scoped (a node has at most one `unit`/`service`
marker pairing and fires at most one REL280/REL281 finding each --
single-instance-per-node, the same carve-out `_reliability.py`'s REL210/
REL211 HEALTH pair already establishes for the IDENTICAL population, NOT
registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL280 missing golden-signal SLO + error budget: a long-lived
    service/daemon node (`_UNIT_ATTR`/`_SERVICE_ATTR`, T-0261 std.host
    surface -- the SAME population `_reliability.py`'s REL210/REL211
    apply to) with no `slo` attr, no `error_budget` attr, or both
    missing. Deny-by-default: a service with no declared golden-signal
    SLOs (latency/traffic/errors/saturation) and error budget has no
    tracked reliability target at all, so a degradation has nothing to
    breach and nothing pages on.
  - REL281 unproven SLO: a node DOES declare both `slo` and
    `error_budget`, but the T-0331 PROVABILITY CONSTRAINT forbids
    discharging it by bare declaration alone -- the node must have at
    least one file bound to it (`_obligation_proof.py::
    node_has_bound_code`) containing a real SLO/error-budget-shaped
    token. A node with no bound code at all is UNCHECKABLE, not
    unproven -- the same ceiling REL201/REL222/REL231/REL261/REL271
    draw.

SCOPE NOTE ON THE STATED DEPENDENCY: the ticket body notes an SLO without
the underlying signal is unverifiable, hence `blocked_by` T-0647
(OBSERVABILITY). This module does NOT hard-wire a runtime check against
T-0647's `observability` marker on the node's inbound/outbound flows --
`KernelModel` has no node-level "this node's flows are instrumented"
projection today, and adding one is a `_facts.py`/kernel-shape change
outside this ticket's `src/frob/strata/**` rule-module scope (charter law
1: no new kernel field smuggled in through a rule module). The dependency
is honored at the OBLIGATION-ORDERING level instead (T-0647 landed first,
in the SAME ticket batch, so a modeler declaring `slo`/`error_budget` on
a service already has REL270/REL271/REL272 checking that service's flows
independently) -- REL280/REL281 read `_UNIT_ATTR`/`_SERVICE_ATTR` and
`slo`/`error_budget` exactly as declared, the same "ship what current
tooling supports" honesty line every other REL2xx rule in this family
already establishes.

GRAMMAR-DATA CEILING, HONESTLY: `slo`/`error_budget` are both presence-
only bare Node attrs (no numeric magnitude -- the same digit-led-literal
ceiling `strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause
imposes on every other REL2xx marker), so REL280/REL281 prove PRESENCE of
a declared golden-signal-SLO-and-error-budget obligation and its code-
level evidence, not a specific latency/error-rate target or budget
percentage. No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/T-0641/T-0647's).
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
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL280 missing golden-signal SLO + error
#: budget: a service/daemon node missing `slo` and/or `error_budget`.
# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
REL_MISSING_SLO = "REL280"

#: `frob sys audit` rule id for REL281 unproven SLO: a node declares both
#: `slo` and `error_budget`, but its bound code has no real SLO/error-
#: budget-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
REL_UNPROVEN_SLO = "REL281"

#: Every REL28x rule id this module can emit -- this module's own, narrow
#: family for `_apply_slo_waivers`' `in_scope` (the "never a shared
#: superset" discipline `_reliability.py`'s module docstring documents
#: the real regression for).
# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
SLO_RULES: frozenset[str] = frozenset({REL_MISSING_SLO, REL_UNPROVEN_SLO})

#: Node attrs marking a long-lived service/daemon node -- the IDENTICAL
#: population `_reliability.py`'s REL210/REL211 HEALTH pair applies to
#: (T-0261 std.host surface). Local literal copies, not an import from
#: `_reliability.py`, for the same import-isolation reason
#: `_reliability.py::_UNIT_ATTR`/`_SERVICE_ATTR` themselves are local
#: copies of `_host.py`'s markers (module docstring precedent).
_UNIT_ATTR = "unit"
_SERVICE_ATTR = "service"
_DAEMON_ATTRS: frozenset[str] = frozenset({_UNIT_ATTR, _SERVICE_ATTR})

#: Node attr declaring a golden-signal SLO obligation discharged
#: (presence-only, module docstring's grammar-data ceiling).
_SLO_ATTR = "slo"

#: Node attr declaring an error-budget obligation discharged (presence-
#: only, module docstring's grammar-data ceiling).
_ERROR_BUDGET_ATTR = "error_budget"

#: Regex proving a real SLO/error-budget-shaped token in bound source
#: text (REL281) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding), matching common SLO/error-budget-
#: library shapes: a literal `error_budget`/`errorbudget` identifier,
#: `slo`/`sloth` (the Sloth SLO generator), or a `p99`/`p95`/`p50`
#: latency-percentile token. Same honesty line
#: `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already establishes:
#: not a claim the matched token measures the SAME service the node
#: models, only that the node's bound code contains real evidence of an
#: SLO/error-budget construct.
_SLO_TOKEN_RE = re.compile(
    r"(error.?budget|\bslo\b|\bsloth\b|\bp9[0-9]\b|\bp50\b)",
    re.IGNORECASE,
)


# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
class SloViolation(BaseModel):
    """One REL28x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one REL280/REL281 finding each), the same bare-
    rule waiver carve-out REL210/REL211 use. Mirrors
    `_reliability.py::ReliabilityViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
class SloReport(BaseModel):
    """Every UNWAIVED REL28x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_reliability.py::ReliabilityReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[SloViolation, ...] = ()
    waived: tuple[SloViolation, ...] = ()


def _is_daemon(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `unit` or `service` marker --
    the REL280/REL281 population (module docstring, identical to REL210/
    REL211's)."""
    return bool(_DAEMON_ATTRS & set(attrs))


def _has_slo(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `slo` marker."""
    return _SLO_ATTR in attrs


def _has_error_budget(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `error_budget` marker."""
    return _ERROR_BUDGET_ATTR in attrs


def _has_full_slo(attrs: tuple[str, ...]) -> bool:
    """Whether a node declares BOTH `slo` and `error_budget` -- REL280 is
    discharged only when both markers are present (module docstring: a
    golden-signal SLO with no error budget, or vice versa, is half a
    reliability target)."""
    return _has_slo(attrs) and _has_error_budget(attrs)


def _missing_slo_violations(model: KernelModel) -> list[SloViolation]:
    """REL280: every service/daemon node missing `slo` and/or
    `error_budget`."""
    violations: list[SloViolation] = []
    for node in model.nodes:
        if not _is_daemon(node.attrs) or _has_full_slo(node.attrs):
            continue
        _log.warning(
            "slo: REL280 node %s is a service with no golden-signal SLO + error budget",
            node.id,
        )
        violations.append(
            SloViolation(
                rule=REL_MISSING_SLO,
                node=node.id,
                detail=(
                    f"node {node.id} is a service with no golden-signal SLO + "
                    "error budget obligation (missing `slo` and/or "
                    "`error_budget` attr)"
                ),
            )
        )
    return violations


def _unproven_slo_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[SloViolation]:
    """REL281: every service/daemon node declaring both `slo` and
    `error_budget` with bound code, but whose bound code carries no real
    SLO/error-budget-shaped token (PROVABILITY CONSTRAINT). Mirrors
    `_circuit_breaker.py::_unproven_circuit_breaker_violations` exactly,
    parameterized on `_SLO_TOKEN_RE`."""
    violations: list[SloViolation] = []
    for node in model.nodes:
        if not _is_daemon(node.attrs) or not _has_full_slo(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _SLO_TOKEN_RE):
            continue
        _log.warning(
            "slo: REL281 node %s declares slo+error_budget but bound code has "
            "no real SLO token",
            node.id,
        )
        violations.append(
            SloViolation(
                rule=REL_UNPROVEN_SLO,
                node=node.id,
                detail=(
                    f"node {node.id} declares slo + error_budget, but its "
                    "bound code has no real SLO/error-budget token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_slo_waivers(model: KernelModel, violations: list[SloViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_circuit_breaker.py::_apply_circuit_breaker_waivers`'s pattern reused
    for the REL28x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in SLO_RULES,
    )


# frob:doc \
# docs/strata/reliability.md#rel28x-golden-signal-slo--error-budget-obligation-t-0648
# frob:ticket T-0648
# frob:ticket T-0958
# frob:enforces SDC-7-SLO-BASED-ALERTING
# frob:enforces CHK-GATE-REL280
# frob:enforces CHK-GATE-REL281
# frob:tests \
# tests/unit/strata/test_slo.py::TestMissingSlo.test_service_node_without_slo_fires
def check_slo_obligations(
    model: KernelModel, root: Path
) -> Result[SloReport, StrataError]:
    """The REL28x golden-signal-SLO-obligation entrypoint (T-0648): REL280
    (missing SLO + error budget) and REL281 (declared-but-unproven SLO,
    proof-against-code) across every service/daemon node in `model`,
    waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_circuit_breaker_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[SloViolation] = []
    violations.extend(_missing_slo_violations(model))
    violations.extend(_unproven_slo_violations(model, owner_by_node, root))
    applied = _apply_slo_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, SloViolation)
    _log.info(
        "slo: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(SloReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "REL_MISSING_SLO",
    "REL_UNPROVEN_SLO",
    "SLO_RULES",
    "SloReport",
    "SloViolation",
    "check_slo_obligations",
]
