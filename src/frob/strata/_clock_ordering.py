"""REL37x reliability family: CLOCK/ORDERING-ASSUMPTIONS obligation
across distributed flows (T-0657, child of the T-0331 systems-checks
epic, docs/strata/reliability.md), mirroring `_retry.py`'s REL22x
flow-scoped structure (module docstring precedent, T-0640/T-0641/T-0647:
one rule module per obligation, same `Report`/`Violation` pydantic pair,
registered in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` -- a node can
originate several `clock_dependent` flows, so each fires per-flow).

A flow whose correctness relies on wall-clock ordering/synchronization
across distributed nodes (e.g. "last write wins" using a client
timestamp, or comparing timestamps minted on two different machines to
decide event order) is a hazard the moment clocks drift: NTP skew, VM
migration pauses, and leap-second handling all make wall-clock
comparisons across independent nodes unreliable, silently reordering
events that a naive timestamp-compare assumed were correctly ordered.
Every `Flow` in this grammar already crosses a real process/service
boundary by construction (REL2xx's own module docstring) -- so a flow
between two nodes IS a distributed hop by definition, the same "every
node is its own service" reading `_shared_state.py`'s module docstring
already establishes for REL36x.

THREE RULES, all flow-scoped (a node can originate several
`clock_dependent` flows, so each fires per-flow -- `MULTI_INSTANCE_
WAIVER_FAMILIES` discipline, same as REL200/REL201/REL220/REL221/REL222/
REL270/REL271/REL272):

  - REL370 missing ordering strategy: a flow marked `clock_dependent`
    (this hop's correctness depends on comparing timestamps/wall-clock
    ordering across the two endpoints) with no `ordering_strategy` attr
    declared. Deny-by-default: a clock-dependent flow with no declared
    ordering strategy silently trusts wall-clock comparison across
    independent nodes, which drifts.
  - REL371 unproven ordering strategy: a `clock_dependent` flow DOES
    declare `ordering_strategy`, but the T-0331 PROVABILITY CONSTRAINT
    forbids discharging it by bare declaration alone -- at least one of
    the flow's ENDPOINTS (`src` or `dst`, T-0758 proof-anchoring) must
    have bound code (`_obligation_proof.py::node_has_bound_code`)
    containing a real ordering-strategy-shaped token (a vector/logical
    clock, a Lamport timestamp, a monotonic sequence number, or a
    happens-before/causal-order construct). A flow with NEITHER endpoint
    bound to any code at all is UNCHECKABLE, not unproven -- the same
    ceiling REL201/REL222/REL231/REL261/REL271/REL281/REL291/REL301/
    REL311/REL321/REL331/REL351 draw.
  - REL372 wall-clock-only discharge: a `clock_dependent` flow declares
    `ordering_strategy`, has bound code, and that code DOES carry an
    ordering-shaped token, but the ONLY such token found is a bare
    wall-clock read (`time.time(`/`datetime.now(`/`System.currentTimeMillis`
    with no vector/logical-clock/sequence-number construct alongside it)
    -- a modeler who declares `ordering_strategy` and then implements it
    with nothing but a wall-clock read has re-introduced the exact hazard
    this obligation exists to catch, so this is flagged distinctly from
    REL371's honest "no evidence at all" silence.

GRAMMAR-DATA CEILING, HONESTLY: `clock_dependent`/`ordering_strategy` are
both presence-only bare Flow attrs (no numeric magnitude, no actual clock
algorithm name round-trips through the grammar -- the same digit-led-
literal ceiling every other REL2xx/REL3xx marker in this family
discloses), so REL370/REL371/REL372 prove PRESENCE of a declared
ordering obligation and its code-level evidence, not a specific clock
algorithm. No `strata-core` change needed (this ticket's scope is
`src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**` only, same
as T-0640/.../T-0656's).
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

#: `frob sys audit` rule id for REL370 missing ordering strategy: a
#: `clock_dependent` flow with no `ordering_strategy` attr declared.
# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
REL_MISSING_ORDERING_STRATEGY = "REL370"

#: `frob sys audit` rule id for REL371 unproven ordering strategy: a flow
#: declares `ordering_strategy`, but no bound endpoint's code has a real
#: ordering-shaped token at all (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
REL_UNPROVEN_ORDERING_STRATEGY = "REL371"

#: `frob sys audit` rule id for REL372 wall-clock-only discharge: a flow
#: declares `ordering_strategy` and has bound code with SOME ordering-
#: shaped token, but the only such token is a bare wall-clock read.
# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
REL_WALL_CLOCK_ONLY = "REL372"

#: Every REL37x rule id this module can emit -- this module's own,
#: narrow family for `_apply_clock_ordering_waivers`' `in_scope` (the
#: "never a shared superset" discipline `_reliability.py`'s module
#: docstring documents the real regression for).
# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
CLOCK_ORDERING_RULES: frozenset[str] = frozenset(
    {REL_MISSING_ORDERING_STRATEGY, REL_UNPROVEN_ORDERING_STRATEGY, REL_WALL_CLOCK_ONLY}
)

#: Flow attr marking a hop whose correctness depends on comparing
#: timestamps/wall-clock ordering across the two endpoints.
_CLOCK_DEPENDENT_ATTR = "clock_dependent"

#: Flow attr discharging the REL370 ordering obligation (presence-only,
#: module docstring's grammar-data ceiling).
_ORDERING_STRATEGY_ATTR = "ordering_strategy"

#: Regex proving a real, non-wall-clock ordering-shaped token in bound
#: source text (REL371/REL372) -- deliberately narrow (a syntactic token
#: scan, not a semantic call-argument binding), matching common
#: distributed-ordering constructs: a vector/logical-clock construct, a
#: Lamport timestamp, a monotonic sequence number, or a happens-before/
#: causal-order construct. Same honesty line every sibling REL2xx/REL3xx
#: token regex's docstring already establishes: not a claim the matched
#: token orders the SAME flow the model describes, only that the bound
#: code contains real evidence of a non-wall-clock ordering construct.
_ORDERING_TOKEN_RE = re.compile(
    r"(vector_clock|logical_clock|lamport|sequence_number|seq_no|"
    r"happens_before|causal_order|hybrid_logical_clock|\bhlc\b)",
    re.IGNORECASE,
)

#: Regex proving a BARE wall-clock read in bound source text (REL372) --
#: the anti-pattern this obligation exists to catch: a modeler declares
#: `ordering_strategy` and implements it with nothing but a raw wall-
#: clock read, which re-introduces clock-drift risk. Matched only when
#: `_ORDERING_TOKEN_RE` finds nothing (module docstring: REL372 is
#: "wall-clock ONLY", not "wall-clock present").
_WALL_CLOCK_TOKEN_RE = re.compile(
    r"(time\.time\(|datetime\.now\(|datetime\.utcnow\(|"
    r"System\.currentTimeMillis|Date\.now\()",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
class ClockOrderingViolation(BaseModel):
    """One REL37x finding: rule id, the reporting node (the flow's `src`),
    a human-readable detail, and `sub_target` (always the flow id --
    every REL37x rule is flow-scoped). Mirrors
    `_retry.py::RetryViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
class ClockOrderingReport(BaseModel):
    """Every UNWAIVED REL37x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_retry.py::RetryReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ClockOrderingViolation, ...] = ()
    waived: tuple[ClockOrderingViolation, ...] = ()


def _is_clock_dependent(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `clock_dependent` marker."""
    return _CLOCK_DEPENDENT_ATTR in attrs


def _has_ordering_strategy(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `ordering_strategy` marker."""
    return _ORDERING_STRATEGY_ATTR in attrs


def _missing_ordering_strategy_violations(
    model: KernelModel,
) -> list[ClockOrderingViolation]:
    """REL370: every `clock_dependent` flow with no `ordering_strategy`
    attr."""
    violations: list[ClockOrderingViolation] = []
    for flow in model.flows:
        if not _is_clock_dependent(flow.attrs) or _has_ordering_strategy(flow.attrs):
            continue
        _log.warning(
            "clock_ordering: REL370 flow %s (%s -> %s) is clock-dependent "
            "with no ordering strategy",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            ClockOrderingViolation(
                rule=REL_MISSING_ORDERING_STRATEGY,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) is marked "
                    "clock_dependent with no declared ordering-strategy "
                    "obligation (no `ordering_strategy` attr)"
                ),
            )
        )
    return violations


def _bound_and_proven_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ClockOrderingViolation]:
    """REL371/REL372: every `clock_dependent` flow declaring
    `ordering_strategy` with at least one bound endpoint. REL371 fires
    when NO bound endpoint's code carries any real ordering-shaped token
    at all (UNCHECKABLE stays silent, same as `_retry.py`'s REL222).
    REL372 fires when a token IS found but it is ONLY a bare wall-clock
    read (module docstring's anti-pattern)."""
    violations: list[ClockOrderingViolation] = []
    for flow in model.flows:
        if not _is_clock_dependent(flow.attrs) or not _has_ordering_strategy(
            flow.attrs
        ):
            continue
        endpoints = bound_endpoints(flow.src, flow.dst, owner_by_node)
        if not endpoints:
            continue
        has_real_token = any(
            files_evidence_token(owner_by_node[node], root, _ORDERING_TOKEN_RE)
            for node in endpoints
        )
        if has_real_token:
            continue
        has_wall_clock_only = any(
            files_evidence_token(owner_by_node[node], root, _WALL_CLOCK_TOKEN_RE)
            for node in endpoints
        )
        reporting_node = endpoints[0]
        if has_wall_clock_only:
            _log.warning(
                "clock_ordering: REL372 flow %s declares ordering_strategy "
                "but bound endpoint(s) %s only have a bare wall-clock read",
                flow.id,
                endpoints,
            )
            violations.append(
                ClockOrderingViolation(
                    rule=REL_WALL_CLOCK_ONLY,
                    node=reporting_node,
                    sub_target=flow.id,
                    detail=(
                        f"flow {flow.id} declares ordering_strategy, but bound "
                        f"endpoint(s) {endpoints}'s code only has a bare "
                        "wall-clock read (time.time()/datetime.now()-shaped), "
                        "no vector/logical-clock or sequence-number construct "
                        "-- re-introduces the clock-drift hazard"
                    ),
                )
            )
            continue
        _log.warning(
            "clock_ordering: REL371 flow %s declares ordering_strategy but "
            "bound endpoint(s) %s have no real ordering token",
            flow.id,
            endpoints,
        )
        violations.append(
            ClockOrderingViolation(
                rule=REL_UNPROVEN_ORDERING_STRATEGY,
                node=reporting_node,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} declares ordering_strategy, but bound "
                    f"endpoint(s) {endpoints}'s code has no real ordering-"
                    "strategy token (proof-against-code, T-0331 PROVABILITY "
                    "CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_clock_ordering_waivers(
    model: KernelModel, violations: list[ClockOrderingViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_retry.py::_apply_retry_waivers`'s pattern reused for the REL37x
    family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in CLOCK_ORDERING_RULES,
    )


# frob:doc docs/strata/reliability.md#rel37x-clockordering-assumptions-obligation-t-0657
# frob:ticket T-0657
# frob:ticket T-0958
# frob:enforces SDC-8-ORDERING-GUARANTEES
# frob:enforces CHK-GATE-REL370
# frob:enforces CHK-GATE-REL371
# frob:enforces CHK-GATE-REL372
# frob:tests tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy.test_clock_dependent_flow_without_ordering_strategy_fires  # noqa: E501
def check_clock_ordering_obligations(
    model: KernelModel, root: Path
) -> Result[ClockOrderingReport, StrataError]:
    """The REL37x CLOCK/ORDERING-ASSUMPTIONS-obligation entrypoint
    (T-0657): REL370 (missing ordering strategy), REL371 (declared-but-
    unproven ordering strategy, proof-against-code), and REL372 (a
    proven-but-wall-clock-only discharge) across every `clock_dependent`
    flow in `model`, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_retry_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[ClockOrderingViolation] = []
    violations.extend(_missing_ordering_strategy_violations(model))
    violations.extend(_bound_and_proven_violations(model, owner_by_node, root))
    applied = _apply_clock_ordering_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, ClockOrderingViolation)
    _log.info(
        "clock_ordering: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        ClockOrderingReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "CLOCK_ORDERING_RULES",
    "REL_MISSING_ORDERING_STRATEGY",
    "REL_UNPROVEN_ORDERING_STRATEGY",
    "REL_WALL_CLOCK_ONLY",
    "ClockOrderingReport",
    "ClockOrderingViolation",
    "check_clock_ordering_obligations",
]
