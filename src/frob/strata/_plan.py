"""`frob sys plan`: obligation -> ticket compiler (T-0084,
docs/strata/surface.md#refinement-hierarchical-models,
docs/strata/roadmap.md phase 5).

The planning frontier is exactly the unrefined frontier
(docs/strata/surface.md: "implementation cannot begin on an undecomposed
box; the unrefined frontier is exactly the planning frontier"), widened
here to every obligation a design model can leave outstanding without a
test ever running:

- **unrefined** -- an `abstract` node with no matching `refine` block
  (surface.md's "Unrefined frontier" elaboration warning).
- **refuted** -- a claim `evaluate_claims` returns as `Verdict.REFUTED`.
- **threat** -- a `THREAT003` violation (`evaluate_threats`): a fired
  capability obligation with no discharging claim at the required rung.
- **unbound** -- a `boundary`/`secret` construct in the design with no
  `frob:boundary`/`frob:secret` code directive anywhere (the SYS002
  question; the raw `(kind, id)` detection is `_design_load.
  unbound_constructs`, shared with `frob.gates.sys_gate`'s SYS002 so the
  join lives in exactly one place, T-0084 review finding 1).

Each frontier item compiles to one parent `PlannedTicket` plus zero or
more child `PlannedTicket`s naming its concrete next action. Every
`PlannedTicket` carries a stable `marker` (`sys-plan:<qualname>:<kind>`)
that `frob.app.sys_runner` matches against existing ticket bodies before
writing anything -- re-running `plan_obligations` against an unchanged
model must compile the identical marker set, so the idempotency contract
lives entirely in that marker being a pure function of the model, never
of wall-clock time or ticket-store state (this module never reads the
ticket store itself; that join is the runner's job, T-0084 scope note).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typani.result import Err, Ok, Result

from frob.graph import EdgeKind, GraphSnapshot
from frob.logging import get_logger
from frob.tickets._models import Stride, TicketKind

from ._claims import evaluate_claims
from ._design_load import DesignIds, unbound_constructs
from ._errors import StrataError
from ._models import KernelModel, Verdict

_log = get_logger(__name__)

# frob:doc docs/commands/sys.md#public-api
#: Every planned ticket's body carries exactly one line starting with this
#: prefix -- the idempotency join key (module docstring).
MARKER_PREFIX = "sys-plan:"


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
@dataclass(frozen=True)
class PlannedTicket:
    """One ticket `frob sys plan` would create: a stable marker, its
    content, and (for a child) the marker of the parent it belongs under."""

    marker: str
    title: str
    kind: TicketKind
    body: str
    scope: tuple[str, ...] = ()
    blocked_by_markers: tuple[str, ...] = ()
    parent_marker: str | None = None
    threat: Stride | None = None


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
@dataclass(frozen=True)
class PlanResult:
    """Every `PlannedTicket` `plan_obligations` compiled, in stable order."""

    tickets: tuple[PlannedTicket, ...] = field(default_factory=tuple)


def _marker(qualname: str, kind: str) -> str:
    """The stable `sys-plan:<qualname>:<kind>` idempotency key for one obligation."""
    return f"{MARKER_PREFIX}{qualname}:{kind}"


def _node_scope(node) -> tuple[str, ...]:  # noqa: ANN001
    """A node's `code=<glob>` attrs, stripped to bare globs (empty if none declared)."""
    return tuple(a[len("code=") :] for a in node.attrs if a.startswith("code="))


def _scope_for_ids(model: KernelModel, ids: tuple[str, ...]) -> tuple[str, ...]:
    """The union of `code=` globs for every node named in `ids` (e.g. a claim's
    counterexample path) -- "scope from counterexample paths" (T-0084 body)."""
    wanted = set(ids)
    globs: set[str] = set()
    for node in model.nodes:
        if node.id in wanted:
            globs.update(_node_scope(node))
    # frob:waive PERF004 reason="one sort of the final glob set, not per-iteration"
    return tuple(sorted(globs))


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
def _frontier_unrefined(model: KernelModel) -> list[PlannedTicket]:
    """One parent+child ticket pair per `abstract` node with no `refine` block
    left in the flattened kernel model (surface.md's "Unrefined frontier")."""
    out: list[PlannedTicket] = []
    for node in model.nodes:
        if "abstract" not in node.attrs:
            continue
        out.extend(_unrefined_frontier_pair(node))
    return out


def _unrefined_frontier_pair(node) -> tuple[PlannedTicket, PlannedTicket]:  # noqa: ANN001
    """The parent+child `PlannedTicket` pair for one unrefined `abstract`
    node, split out of `_frontier_unrefined` purely to keep its loop body
    short."""
    scope = _node_scope(node)
    parent = _marker(node.id, "unrefined")
    child = _marker(node.id, "refine")
    return (
        _unrefined_parent_ticket(node, parent, scope),
        _unrefined_child_ticket(node, parent, child, scope),
    )


def _unrefined_parent_ticket(  # noqa: ANN001
    node, marker: str, scope: tuple[str, ...]
) -> PlannedTicket:
    """The parent `PlannedTicket` for one unrefined `abstract` node."""
    return PlannedTicket(
        marker=marker,
        title=f"Refine abstract component {node.id}",
        kind=TicketKind.FEATURE,
        body=(
            f"{marker}\n\n"
            f"Component `{node.id}` is on the unrefined frontier: it has "
            "no matching `refine` block, so implementation cannot begin "
            "on it (docs/strata/surface.md#refinement-hierarchical-"
            "models). This is the planning frontier, per surface.md."
        ),
        scope=scope,
    )


def _unrefined_child_ticket(
    node,  # noqa: ANN001
    parent_marker: str,
    marker: str,
    scope: tuple[str, ...],
) -> PlannedTicket:
    """The child `PlannedTicket` for one unrefined `abstract` node."""
    return PlannedTicket(
        marker=marker,
        title=f"Decompose {node.id} via refine block",
        kind=TicketKind.FEATURE,
        body=(
            f"{marker}\n\n"
            f"Write `refine {node.id} into {{ ... binds {node.id} = ... }}` "
            "satisfying faithfulness: no new external surface, no trust "
            "laundering, budget distribution "
            "(docs/strata/surface.md#v0-semantics)."
        ),
        scope=scope,
        parent_marker=parent_marker,
        blocked_by_markers=(parent_marker,),
    )


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
def _frontier_refuted(model: KernelModel) -> Result[list[PlannedTicket], StrataError]:
    """One ticket per `Verdict.REFUTED` claim, scoped to the counterexample path."""
    evaluated = evaluate_claims(model)
    if evaluated.is_err:
        _log.warning("plan: evaluate_claims failed: %s", evaluated.danger_err)
        return Err(evaluated.danger_err)
    out: list[PlannedTicket] = []
    for result in evaluated.danger_ok:
        if result.verdict != Verdict.REFUTED:
            continue
        marker = _marker(result.claim_id, "refuted")
        path = " -> ".join(result.counterexample) or "(none)"
        out.append(
            PlannedTicket(
                marker=marker,
                title=f"Fix refuted claim {result.claim_id}",
                kind=TicketKind.BUG,
                body=(
                    f"{marker}\n\n"
                    f"Claim `{result.claim_id}` is REFUTED: {result.detail}\n"
                    f"Counterexample path: {path}"
                ),
                scope=_scope_for_ids(model, result.counterexample),
            )
        )
    return Ok(out)


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
def _frontier_threats(
    model: KernelModel, view: str
) -> Result[list[PlannedTicket], StrataError]:
    """One ticket per `THREAT003` violation: a fired-but-undischarged capability
    obligation (`evaluate_threats`, reused read-only per T-0084 scope)."""
    from ._threat import evaluate_threats

    report = evaluate_threats(model, view)
    if report.is_err:
        _log.warning("plan: evaluate_threats failed: %s", report.danger_err)
        return Err(report.danger_err)
    out: list[PlannedTicket] = []
    for violation in report.danger_ok.violations:
        if violation.rule != "THREAT003":
            continue
        qualname = f"{violation.node}:{violation.cwe}"
        marker = _marker(qualname, "threat")
        scope = _scope_for_ids(model, (violation.node,)) if violation.node else ()
        out.append(
            PlannedTicket(
                marker=marker,
                title=f"Discharge {violation.cwe} at {violation.node}",
                kind=TicketKind.SECURITY,
                body=f"{marker}\n\n{violation.detail}",
                scope=scope,
            )
        )
    return Ok(out)


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
def _frontier_unbound(
    design_ids: DesignIds, snapshot: GraphSnapshot
) -> list[PlannedTicket]:
    """One ticket per boundary/secret construct with no `frob:boundary`/
    `frob:secret` code directive anywhere -- the SYS002 question, detected
    via the shared `_design_load.unbound_constructs` join (also used by
    `frob.gates.sys_gate`'s SYS002, T-0084 review finding 1)."""
    out: list[PlannedTicket] = []
    for kind, construct_id in unbound_constructs(design_ids, snapshot):
        marker = _marker(construct_id, "unbound")
        out.append(
            PlannedTicket(
                marker=marker,
                title=f"Bind {kind.value} {construct_id} in code",
                kind=TicketKind.SECURITY,
                body=(
                    f"{marker}\n\n"
                    f"{kind.value} `{construct_id}` has no code binding; add "
                    f"`frob:{kind.value} {construct_id}` at the enforcing site "
                    "(docs/strata/surface.md#directives-t-0080)."
                ),
                threat=Stride.TAMPERING
                if kind == EdgeKind.BOUNDARY
                else Stride.INFO_DISCLOSURE,
            )
        )
    return out


# frob:doc docs/strata/surface.md#refinement-hierarchical-models
# frob:ticket T-0084
# frob:tests tests/unit/strata/test_plan.py::TestPlanObligations.test_unrefined_frontier
# frob:tests tests/unit/strata/test_plan.py::TestPlanObligations.test_refuted_claim
# frob:tests tests/unit/strata/test_plan.py::TestPlanObligations.test_unbound_boundary
# frob:tests tests/unit/strata/test_plan.py::TestPlanObligations.test_idempotent_markers
# frob:waive TEST005 reason="plan_obligations 83.3% branch cover, debt T-0160"
def plan_obligations(
    model: KernelModel,
    *,
    design_ids: DesignIds | None = None,
    snapshot: GraphSnapshot | None = None,
    view: str = "owasp-top-10",
) -> Result[PlanResult, StrataError]:
    """Compile `model`'s obligation frontier into a flat, marker-keyed
    `PlanResult`: unrefined abstract nodes, REFUTED claims, fired-but-
    undischarged `THREAT003` obligations, and (when `design_ids`+`snapshot`
    are given) unbound boundaries/secrets. Pure function of `model` (plus
    the optional design/graph views) -- calling it twice on an unchanged
    model yields the identical marker set, which is the whole idempotency
    contract the caller (`frob.app.sys_runner`) relies on.
    """
    tickets: list[PlannedTicket] = list(_frontier_unrefined(model))

    refuted = _frontier_refuted(model)
    if refuted.is_err:
        return Err(refuted.danger_err)
    tickets.extend(refuted.danger_ok)

    threats = _frontier_threats(model, view)
    if threats.is_err:
        return Err(threats.danger_err)
    tickets.extend(threats.danger_ok)

    if design_ids is not None and snapshot is not None:
        tickets.extend(_frontier_unbound(design_ids, snapshot))

    _log.info("plan: compiled %d obligation ticket(s) for %r", len(tickets), view)
    return Ok(PlanResult(tickets=tuple(tickets)))


__all__ = ["MARKER_PREFIX", "PlanResult", "PlannedTicket", "plan_obligations"]
