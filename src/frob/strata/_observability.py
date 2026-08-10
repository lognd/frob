"""REL27x reliability family: boundary-flow OBSERVABILITY (metrics+traces+
logs) obligation and trace-id CORRELATION propagation across multi-hop
flow chains (T-0647, child of the T-0331 systems-checks epic, docs/
strata/reliability.md), mirroring `_circuit_breaker.py`/`_retry.py`'s
REL2xx structure (module docstring precedent, T-0699/T-0640/.../T-0646:
one rule module per obligation, same `Report`/`Violation` pydantic pair,
registration/exemption from `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
CLI wiring via `frob.app.sys_runner`).

THREE RULES, all FLOW-scoped (a node can originate/receive several
boundary or chained flows, so each fires per-flow -- the
`MULTI_INSTANCE_WAIVER_FAMILIES` discipline REL200/REL201/REL220/REL221/
REL222 already establish):

  - REL270 missing observability: a flow attached to a `Boundary`
    (`KernelModel.boundaries`, the only legal site of label/trust change,
    `_models.py::Boundary`) with no `observability` attr declared. Deny-
    by-default: a boundary crossing with no metrics/traces/logs
    instrumentation is an unobserved trust/label change -- the exact
    blind spot an incident review cannot reconstruct after the fact.
  - REL271 unproven observability: a flow DOES declare `observability`,
    but the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- at least one of the flow's endpoints (`src` or
    `dst`, T-0758 proof-anchoring) must have bound code
    (`_obligation_proof.py::node_has_bound_code`) containing a real
    metrics/tracing/logging-shaped token. A flow with NEITHER endpoint
    bound to any code at all is UNCHECKABLE, not unproven -- the same
    ceiling REL201/REL222/REL231/REL261 draw.
  - REL272 missing correlation propagation: a flow that is NOT the first
    hop of its chain (some OTHER flow's `dst` equals this flow's `src`,
    i.e. this flow continues a multi-hop path) with no `correlation` attr
    declared. Deny-by-default: a chained call with no propagated trace-id
    breaks distributed tracing at exactly the hop boundary that matters
    most for cross-service debugging.

`observability` and `correlation` are deliberately TWO separate Flow
attrs, not one combined marker: a single-hop boundary flow can need
observability without ever being part of a chain (REL270 alone applies),
and an internal (non-boundary) chained hop can need correlation
propagation without crossing any trust/label boundary (REL272 alone
applies) -- conflating them would either over-fire on isolated boundary
hops or under-fire on internal chain links.

GRAMMAR-DATA CEILING, HONESTLY: `observability`/`correlation` are both
presence-only bare Flow attrs (no numeric magnitude, no actual trace-id
format round-trips through the grammar -- the same digit-led-literal
ceiling `strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause
imposes on every other REL2xx marker), so REL270/REL271/REL272 prove
PRESENCE of a declared instrumentation/propagation obligation and its
code-level evidence (REL271 only), not a specific metric name or trace
header format. No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/T-0641/T-0646's).
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
from ._obligation_proof import bound_endpoints, files_evidence_token, owner_index
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL270 missing observability: a boundary
#: flow with no `observability` attr declared.
# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
REL_MISSING_OBSERVABILITY = "REL270"

#: `frob sys audit` rule id for REL271 unproven observability: a flow
#: declares `observability`, but its bound endpoint code has no real
#: metrics/tracing/logging-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
REL_UNPROVEN_OBSERVABILITY = "REL271"

#: `frob sys audit` rule id for REL272 missing correlation propagation: a
#: chained (non-first-hop) flow with no `correlation` attr declared.
# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
REL_MISSING_CORRELATION = "REL272"

#: Every REL27x rule id this module can emit -- this module's own, narrow
#: family for `_apply_observability_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
OBSERVABILITY_RULES: frozenset[str] = frozenset(
    {REL_MISSING_OBSERVABILITY, REL_UNPROVEN_OBSERVABILITY, REL_MISSING_CORRELATION}
)

#: Flow attr discharging the REL270 metrics+traces+logs obligation
#: (presence-only, module docstring's grammar-data ceiling).
_OBSERVABILITY_ATTR = "observability"

#: Flow attr discharging the REL272 trace-id correlation-propagation
#: obligation (presence-only, module docstring's grammar-data ceiling).
_CORRELATION_ATTR = "correlation"

#: Regex proving a real metrics/tracing/logging-shaped token in bound
#: source text (REL271) -- deliberately narrow (a syntactic token scan,
#: not a semantic call-argument binding), matching common observability-
#: library shapes: `prometheus`/`statsd`, `opentelemetry`/`otel`, a
#: `tracer.start_span(`/`with tracer.start_as_current_span(` call, or a
#: `logger.`/`logging.` call site. Same honesty line
#: `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already establishes:
#: not a claim the matched token instruments the SAME flow the model
#: describes, only that the bound endpoint's code contains real evidence
#: of an observability construct.
_OBSERVABILITY_TOKEN_RE = re.compile(
    r"(prometheus|statsd|opentelemetry|\botel\b|tracer\.start|"
    r"start_as_current_span|\blogger\.|\blogging\.)",
    re.IGNORECASE,
)


# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
class ObservabilityViolation(BaseModel):
    """One REL27x finding: rule id, the reporting node, a human-readable
    detail, and `sub_target` (always the flow id -- every REL27x rule is
    flow-scoped). Mirrors `_retry.py::RetryViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
class ObservabilityReport(BaseModel):
    """Every UNWAIVED REL27x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_retry.py::RetryReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ObservabilityViolation, ...] = ()
    waived: tuple[ObservabilityViolation, ...] = ()


def _boundary_flow_ids(model: KernelModel) -> frozenset[str]:
    """Every flow id with a `Boundary` attached (`Boundary.flow_id`) --
    the REL270/REL271 population (module docstring)."""
    return frozenset(boundary.flow_id for boundary in model.boundaries)


def _has_observability(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `observability` marker."""
    return _OBSERVABILITY_ATTR in attrs


def _has_correlation(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `correlation` marker."""
    return _CORRELATION_ATTR in attrs


def _missing_observability_violations(
    model: KernelModel,
) -> list[ObservabilityViolation]:
    """REL270: every boundary flow with no `observability` attr."""
    boundary_flow_ids = _boundary_flow_ids(model)
    violations: list[ObservabilityViolation] = []
    for flow in model.flows:
        if flow.id not in boundary_flow_ids or _has_observability(flow.attrs):
            continue
        _log.warning(
            "observability: REL270 boundary flow %s (%s -> %s) has no "
            "observability obligation",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            ObservabilityViolation(
                rule=REL_MISSING_OBSERVABILITY,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"boundary flow {flow.id} ({flow.src} -> {flow.dst}) has no "
                    "metrics/traces/logs obligation (no `observability` attr)"
                ),
            )
        )
    return violations


def _unproven_observability_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ObservabilityViolation]:
    """REL271: every boundary flow declaring `observability` where at
    least one endpoint has bound code, but none of the bound endpoints'
    code carries a real observability-shaped token (PROVABILITY
    CONSTRAINT). Mirrors `_retry.py::_unproven_backoff_violations`
    exactly, parameterized on `_OBSERVABILITY_TOKEN_RE`."""
    boundary_flow_ids = _boundary_flow_ids(model)
    violations: list[ObservabilityViolation] = []
    for flow in model.flows:
        if flow.id not in boundary_flow_ids or not _has_observability(flow.attrs):
            continue
        endpoints = bound_endpoints(flow.src, flow.dst, owner_by_node)
        if not endpoints:
            continue
        if any(
            files_evidence_token(owner_by_node[node], root, _OBSERVABILITY_TOKEN_RE)
            for node in endpoints
        ):
            continue
        reporting_node = endpoints[0]
        _log.warning(
            "observability: REL271 flow %s declares observability but bound "
            "endpoint(s) %s have no real observability token",
            flow.id,
            endpoints,
        )
        violations.append(
            ObservabilityViolation(
                rule=REL_UNPROVEN_OBSERVABILITY,
                node=reporting_node,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} declares observability, but bound "
                    f"endpoint(s) {endpoints}'s code has no real metrics/"
                    "tracing/logging token (proof-against-code, T-0331 "
                    "PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _chained_flow_ids(model: KernelModel) -> frozenset[str]:
    """Every flow id that is NOT the first hop of its chain -- some OTHER
    flow's `dst` equals this flow's `src` (module docstring: REL272's
    population). A flow whose `src` no other flow ever reaches is a chain
    origin and is exempt (nothing to propagate a correlation id FROM)."""
    upstream_dsts = {flow.dst for flow in model.flows}
    return frozenset(
        flow.id
        for flow in model.flows
        if flow.src in upstream_dsts and flow.src != flow.dst
    )


def _missing_correlation_violations(model: KernelModel) -> list[ObservabilityViolation]:
    """REL272: every chained (non-first-hop) flow with no `correlation`
    attr -- a chained call with no propagated trace-id breaks distributed
    tracing at exactly the hop that matters most."""
    chained_ids = _chained_flow_ids(model)
    violations: list[ObservabilityViolation] = []
    for flow in model.flows:
        if flow.id not in chained_ids or _has_correlation(flow.attrs):
            continue
        _log.warning(
            "observability: REL272 chained flow %s (%s -> %s) has no "
            "correlation propagation",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            ObservabilityViolation(
                rule=REL_MISSING_CORRELATION,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"chained flow {flow.id} ({flow.src} -> {flow.dst}) has no "
                    "trace-id correlation propagation (no `correlation` attr)"
                ),
            )
        )
    return violations


def _apply_observability_waivers(
    model: KernelModel, violations: list[ObservabilityViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_retry.py::_apply_retry_waivers`'s pattern reused for the REL27x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in OBSERVABILITY_RULES,
    )


# frob:doc \
# docs/strata/reliability.md#rel27x-observability--correlation-obligation-t-0647
# frob:ticket T-0647
# frob:ticket T-0958
# frob:enforces SDC-6-USE-METHOD-UTILIZATION-SATURATION-ERRORS
# frob:enforces SDC-7-THREE-PILLARS-METRICS-LOGS-TRACES
# frob:enforces SDC-7-DISTRIBUTED-TRACING-DAPPER
# frob:enforces CHK-GATE-REL270
# frob:enforces CHK-GATE-REL271
# frob:enforces CHK-GATE-REL272
# frob:tests tests/unit/strata/test_observability.py::TestMissingObservability.test_boundary_flow_without_observability_fires  # noqa: E501
def check_observability_obligations(
    model: KernelModel, root: Path
) -> Result[ObservabilityReport, StrataError]:
    """The REL27x observability+correlation entrypoint (T-0647): REL270
    (missing observability), REL271 (declared-but-unproven observability,
    proof-against-code), and REL272 (missing correlation propagation on a
    chained flow) across `model`, waivers already applied. `root` is the
    repo root `_code_binding.py::bind_code` binds against -- `Err`
    propagates `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by
    default, the same discipline `check_retry_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[ObservabilityViolation] = []
    violations.extend(_missing_observability_violations(model))
    violations.extend(_unproven_observability_violations(model, owner_by_node, root))
    violations.extend(_missing_correlation_violations(model))
    applied = _apply_observability_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, ObservabilityViolation)
    _log.info(
        "observability: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        ObservabilityReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "OBSERVABILITY_RULES",
    "REL_MISSING_CORRELATION",
    "REL_MISSING_OBSERVABILITY",
    "REL_UNPROVEN_OBSERVABILITY",
    "ObservabilityReport",
    "ObservabilityViolation",
    "check_observability_obligations",
]
