"""REL31x reliability family: INTERACTIVE-COST-BOUND obligation on
`interactive` nodes (T-0919, sibling to the REL26x BACKPRESSURE family
`_backpressure.py` established for T-0646), mirroring that module's
structure (module docstring precedent, T-0646/T-0699/T-0640/...: one rule
module per obligation, same `Report`/`Violation` pydantic pair,
registration/exemption from `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`,
CLI wiring left as its own follow-up ticket -- same posture `_backpressure.
py`/`_txn.py`/`_ssot.py` are already in, not yet threaded into
`frob.app.sys_runner._run_audit`).

Motivated directly by the T-0919 incident this obligation family exists to
generalize: `frob ticket done-report`'s CLI path -- a node a human sits in
front of a foreground shell waiting on -- spawned TWO SEPARATE full `frob
check --ticket <id>` subprocesses (600s timeout each) serially, for output
fully re-derivable from one run. The root problem is not specific to that
one command: ANY node marked `interactive` (a human-facing CLI/foreground
flow, as opposed to a background job whose latency nobody watches live)
has an implicit obligation that its OWN cost is bounded and not
needlessly duplicated -- an unbounded or duplicated-spawn interactive flow
is a foreground-hang risk exactly like an unbounded queue (REL26x) is an
OOM risk.

TWO RULES, both NODE-scoped (a node has at most one `interactive` marker
and fires at most one REL310/REL311 finding each -- single-instance-per-
node, the same carve-out `_backpressure.py`'s REL260/REL261 pair
establishes, NOT registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL310 missing bounded cost: a node marked `interactive` (this node is
    a human-facing CLI/foreground command or flow) with no `bounded_cost`
    attr declared. Deny-by-default: an interactive flow with no declared
    cost bound can silently grow (a new internal spawn added later, a
    doubled call site like T-0919's) until it blows past any reasonable
    foreground wait, with nothing statically flagging the drift.
  - REL311 unproven bounded cost: a node DOES declare `bounded_cost`, but
    the T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- the node must have at least one file bound to it
    (`_obligation_proof.py::node_has_bound_code`) containing a real
    cost-bounding-shaped token (a shared/deduplicated spawn, a cache/memo,
    an explicit timeout, or a stage-scoped/`--only`-style narrowing -- see
    `_BOUNDED_COST_TOKEN_RE`). A node with no bound code at all is
    UNCHECKABLE, not unproven -- the same ceiling REL201/REL222/REL231/
    REL261 draw.

GRAMMAR-DATA CEILING, HONESTLY: `interactive`/`bounded_cost` are both bare
Node attrs (no numeric magnitude -- the same digit-led-literal ceiling
`strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause imposes on
every other REL2xx/REL3xx marker), so REL310/REL311 prove PRESENCE of a
declared cost-bound obligation and its code-level evidence, not a
specific wall-clock budget. No `strata-core` change needed (this ticket's
scope is `src/frob/strata/**`/`docs/strata/**`/`tests/unit/strata/**`
only, same as T-0646/T-0640/T-0641/T-0642's).
"""
# frob:waive INV006 reason="T-0919 first-turn-on: this module's 'only'/ 'deliberately \
# narrow' hits are source-level design-rationale/scope-cut prose mirroring \
# _backpressure.py's own identical waiver for the identical reason (module docstring \
# precedent), not a separate cross-module contract"

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

#: `frob sys audit` rule id for REL310 missing bounded cost: an
#: `interactive` node with no `bounded_cost` attr declared.
# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
REL_MISSING_BOUNDED_COST = "REL310"

#: `frob sys audit` rule id for REL311 unproven bounded cost: a node
#: declares `bounded_cost`, but its bound code has no real cost-bounding
#: token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
REL_UNPROVEN_BOUNDED_COST = "REL311"

#: Every REL31x rule id this module can emit -- this module's own, narrow
#: family for `_apply_interactive_cost_waivers`' `in_scope` (the "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
INTERACTIVE_COST_RULES: frozenset[str] = frozenset(
    {REL_MISSING_BOUNDED_COST, REL_UNPROVEN_BOUNDED_COST}
)

#: Node attr marking a human-facing CLI/foreground flow -- the REL310/
#: REL311 population (module docstring).
_INTERACTIVE_ATTR = "interactive"

#: Node attr discharging the REL310 cost-bound obligation (presence-only,
#: module docstring's grammar-data ceiling).
_BOUNDED_COST_ATTR = "bounded_cost"

#: Regex proving a real cost-bounding-shaped token in bound source text
#: (REL311) -- deliberately narrow (a syntactic token scan, not a semantic
#: call-argument binding), matching common cost-bounding shapes: a shared/
#: memoized/deduplicated spawn (`lru_cache`, `memo`, `cache`, a `spawn`
#: variable reused across two calls), an explicit `timeout=`/`--only`
#: stage-narrowing kwarg, or a literal `bounded_cost`/`dedup`/`shared_spawn`
#: identifier. Same honesty line `_backpressure.py::_BOUNDED_INTAKE_TOKEN_
#: RE`'s docstring already establishes: not a claim the matched token
#: bounds the SAME cost the node models, only that the node's bound code
#: contains real evidence of a cost-bounding construct.
_BOUNDED_COST_TOKEN_RE = re.compile(
    r"(lru_cache|\bmemo\b|\bcache\b|shared_spawn|dedup|bounded_cost|"
    r"timeout\s*=|--only\b|\bonce\b)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
class InteractiveCostViolation(BaseModel):
    """One REL31x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one REL310/REL311 finding each), the same bare-rule
    waiver carve-out REL260/REL261 use. Mirrors
    `_backpressure.py::BackpressureViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
class InteractiveCostReport(BaseModel):
    """Every UNWAIVED REL31x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_backpressure.py::BackpressureReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[InteractiveCostViolation, ...] = ()
    waived: tuple[InteractiveCostViolation, ...] = ()


def _is_interactive(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the `interactive` marker -- the
    REL310/REL311 population (module docstring)."""
    return _INTERACTIVE_ATTR in attrs


def _has_bounded_cost(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `bounded_cost` marker."""
    return _BOUNDED_COST_ATTR in attrs


def _missing_bounded_cost_violations(
    model: KernelModel,
) -> list[InteractiveCostViolation]:
    """REL310: every `interactive` node with no `bounded_cost` attr."""
    violations: list[InteractiveCostViolation] = []
    for node in model.nodes:
        if not _is_interactive(node.attrs) or _has_bounded_cost(node.attrs):
            continue
        _log.warning(
            "interactive_cost: REL310 node %s is interactive with no bounded "
            "cost policy",
            node.id,
        )
        violations.append(
            InteractiveCostViolation(
                rule=REL_MISSING_BOUNDED_COST,
                node=node.id,
                detail=(
                    f"node {node.id} is interactive with no bounded-cost "
                    "obligation (no `bounded_cost` attr) -- an unbounded or "
                    "duplicated-spawn interactive flow is a foreground-hang "
                    "risk (T-0919)"
                ),
            )
        )
    return violations


def _unproven_bounded_cost_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[InteractiveCostViolation]:
    """REL311: every `interactive` node declaring `bounded_cost` with bound
    code, but whose bound code carries no real cost-bounding-shaped token
    (PROVABILITY CONSTRAINT). Mirrors `_backpressure.py::
    _unproven_bounded_intake_violations` exactly, parameterized on
    `_BOUNDED_COST_TOKEN_RE`."""
    violations: list[InteractiveCostViolation] = []
    for node in model.nodes:
        if not _is_interactive(node.attrs) or not _has_bounded_cost(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _BOUNDED_COST_TOKEN_RE):
            continue
        _log.warning(
            "interactive_cost: REL311 node %s declares bounded_cost but bound "
            "code has no real bounded-cost token",
            node.id,
        )
        violations.append(
            InteractiveCostViolation(
                rule=REL_UNPROVEN_BOUNDED_COST,
                node=node.id,
                detail=(
                    f"node {node.id} declares bounded_cost, but its bound "
                    "code has no real cost-bounding token (proof-against-code, "
                    "T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_interactive_cost_waivers(
    model: KernelModel, violations: list[InteractiveCostViolation]
):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_backpressure.py::_apply_backpressure_waivers`'s pattern reused for
    the REL31x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in INTERACTIVE_COST_RULES,
    )


# frob:doc docs/strata/reliability.md#rel31x-interactive-cost-bound-obligation-t-0919
# frob:ticket T-0919
# frob:enforces CHK-GATE-REL310
# frob:enforces CHK-GATE-REL311
# frob:tests tests/unit/strata/test_interactive_cost.py::TestMissingBoundedCost.test_interactive_node_without_bounded_cost_fires  # noqa: E501
def check_interactive_cost_obligations(
    model: KernelModel, root: Path
) -> Result[InteractiveCostReport, StrataError]:
    """The REL31x INTERACTIVE-COST-BOUND-obligation entrypoint (T-0919):
    REL310 (missing bounded cost) and REL311 (declared-but-unproven
    bounded cost, proof-against-code) across every `interactive` node in
    `model`, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_backpressure_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[InteractiveCostViolation] = []
    violations.extend(_missing_bounded_cost_violations(model))
    violations.extend(_unproven_bounded_cost_violations(model, owner_by_node, root))
    applied = _apply_interactive_cost_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        InteractiveCostViolation(
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
        "interactive_cost: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        InteractiveCostReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "INTERACTIVE_COST_RULES",
    "REL_MISSING_BOUNDED_COST",
    "REL_UNPROVEN_BOUNDED_COST",
    "InteractiveCostReport",
    "InteractiveCostViolation",
    "check_interactive_cost_obligations",
]
