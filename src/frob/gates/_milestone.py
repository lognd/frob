"""frob.gates._milestone -- MILE00x milestone-resolution gate family
(T-2576 M2).

M2 was originally scoped as a bulk backfill of `milestone: 1.0.0` into
every open ticket file plus MILE003. The coordinator redesigned it
(T-2576's own ticket body, "SCOPE REDESIGN" section): the backfill would
have required a write lease on every ticket file simultaneously, which
could only run with the whole fleet stopped. A read-time default
(`[tickets].default_milestone` in `frob.toml`, resolved by
`frob.tickets._doable.effective_milestone`'s TERMINAL fallback) gives the
identical result with zero ticket-file writes. This module is only the
MILE003 gate on top of that resolution -- M1 (T-2574, `Ticket.milestone`
+ semver ordering) and M3 (T-2577, the declared/inherited walk) already
landed; this module reuses `effective_milestone` verbatim rather than
re-deriving any part of that chain (T-2576's own coordination note: "the
resolution function must have exactly ONE home").
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.tickets import Ticket, TicketQueue, TicketState

_log = get_logger(__name__)

#: Terminal `TicketState`s -- same set `_tickets_gate.py`'s own
#: `_TERMINAL_STATES` uses; duplicated here rather than imported since
#: `_tickets_gate` is a sibling family module, not a shared dependency
#: this one should reach into.
_TERMINAL_STATES = (TicketState.DONE, TicketState.DROPPED)


# frob:ticket T-2576
# frob:tests tests/test_gates_milestone.py::TestMile003.test_fires_on_open_ticket_with_no_resolvable_milestone  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_once_stamped  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_on_configured_default  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_on_inherited_value  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_terminal_ticket_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_no_default_configured_still_fires  # noqa: E501
def _mile003_unresolved_milestone(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE003 (ERROR): one violation per OPEN ticket (any tier -- an
    epic/story with no declared milestone is just as unresolved as a leaf)
    whose EFFECTIVE milestone (`frob.tickets._doable.effective_milestone`,
    given `root` so the configured `[tickets].default_milestone` is
    consulted as the terminal fallback) cannot be RESOLVED: no milestone
    declared on the ticket itself, none on any ancestor, AND no repo
    default configured. This is what stops a new ticket silently skipping
    the field after M1 added it (T-2576's own Description) -- and, per the
    redesign, is now the ONLY enforcement mechanism; nothing backfills the
    ledger to make this vacuously pass.

    Fires on ANY value of `None` from `effective_milestone` regardless of
    the (irrelevant, since there is no value) `MilestoneSource` -- a
    `DECLARED`/`INHERITED`/`DEFAULTED` resolution never reaches here at
    all, `effective_milestone` returned a real string for each of those
    three.

    A terminal ticket (done/dropped, `_TERMINAL_STATES`) never fires --
    it does not sequence again, so an unresolved milestone on it is not a
    live finding (same reasoning T-2576's Description gives for excluding
    terminal tickets from the abandoned backfill).

    `queue` is the gate's already-loaded `TicketQueue` (`st.queue`,
    `run_gates`'s own `_load_graph_queue_lock` step) -- a queue-load
    failure never reaches this function at all; `run_gates` hard-Errs the
    WHOLE run via `GateError.QueueUnavailable` before any gate (this one
    included) runs, so MILE003 finding zero here is never confusable with
    "the queue could not be read" -- that failure mode produces no gate
    report whatsoever, not a clean one. Same defense-in-depth posture
    `_tick001_duplicate_ids`'s own docstring documents for TICK001."""
    from frob.tickets._doable import effective_milestone

    violations: list[Violation] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in _TERMINAL_STATES:
            continue
        milestone, _source = effective_milestone(queue, t, root)
        if milestone is not None:
            continue
        violations.append(
            Violation(
                rule="MILE003",
                severity=Severity.ERROR,
                file="tickets.md",
                line=0,
                message=(
                    f"MILE003: {t.id} ({t.state.value}) has no resolvable "
                    f"milestone -- no `milestone` declared on the ticket "
                    f"itself, none on any ancestor, and this repo "
                    f"configures no `[tickets].default_milestone` in "
                    f"frob.toml; set one with `frob ticket milestone "
                    f"{t.id} --set VALUE`, or configure a repo default"
                ),
            )
        )
    return tuple(violations)


# frob:ticket T-2579
def _ordered(a: Ticket, b: Ticket) -> bool:
    """`True` if `a`/`b` (both `Ticket`) are ordered against each other by
    a real `blocked_by` edge, in EITHER direction -- MILE004's own
    definition of "not ambiguous". A `blocked_by` edge naming an id that
    does not resolve in `queue` never reaches here (the id strings are
    compared directly, no lookup needed)."""
    return a.id in b.blocked_by or b.id in a.blocked_by


# frob:ticket T-2579
def _group_runs_last_by_milestone(
    root: Path, queue: TicketQueue
) -> dict[str, list[Ticket]]:
    """OPEN (non-terminal) `runs_last` tickets grouped by EFFECTIVE
    milestone (`frob.tickets._doable.effective_milestone`) -- MILE004's
    own candidate pool. A `runs_last` ticket with NO resolvable effective
    milestone is excluded (nothing to share a milestone WITH); that
    ticket's own lack of a milestone is MILE003's concern, not this
    one's."""
    from frob.tickets._doable import effective_milestone

    groups: dict[str, list[Ticket]] = {}
    for t in queue.tickets.values():
        if not t.runs_last or t.state in _TERMINAL_STATES:
            continue
        milestone, _source = effective_milestone(queue, t, root)
        if milestone is None:
            continue
        groups.setdefault(milestone, []).append(t)
    return groups


# frob:ticket T-2579
def _mile004_pair_violation(milestone: str, a: Ticket, b: Ticket) -> Violation | None:
    """One MILE004 `Violation` for the `(a, b)` pair if their order is
    AMBIGUOUS -- neither a real `blocked_by` edge between them (either
    direction, `_ordered`) nor an explicit `runs_last_parallel_safe=True`
    declaration on BOTH sides (T-2579's own body: a one-sided declaration
    is not a decision, both tickets must independently claim safety) --
    else `None`."""
    if _ordered(a, b):
        return None
    if a.runs_last_parallel_safe and b.runs_last_parallel_safe:
        return None
    return Violation(
        rule="MILE004",
        severity=Severity.ERROR,
        file="tickets.md",
        line=0,
        message=(
            f"MILE004: {a.id} and {b.id} are both runs_last in milestone "
            f"{milestone} with no ordering between them -- add a "
            f"blocked_by edge (either direction), or declare BOTH "
            f"runs_last_parallel_safe=True with a reason"
        ),
    )


# frob:ticket T-2579
# frob:doc docs/modules/tickets-data-storage.md#mile004-t-2579-m4b
# frob:tests tests/test_gates_milestone.py::TestMile004.test_two_unordered_runs_last_in_one_milestone_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_blocked_by_edge_resolves_the_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_declared_parallel_safe_resolves_the_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_single_runs_last_ticket_never_fires  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_different_milestones_never_pair  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile004.test_terminal_sibling_excluded  # noqa: E501
def _mile004_unordered_runs_last(
    root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """MILE004 (ERROR): flag every PAIR of `runs_last` tickets that share
    one EFFECTIVE milestone and whose relative order is AMBIGUOUS
    (`_mile004_pair_violation`).

    This is a genuinely REQUESTED design (T-2579's body: "do not
    relitigate"), not a rediscovery. The pre-existing T-1613 sibling
    carve-out in `frob.tickets._doable._other_open_tickets` (fellow
    runs-last tickets never count as "open" against each other) is
    UNTOUCHED by this gate -- that carve-out is what lets two runs-last
    tickets coexist as dispatchable candidates at all; MILE004 only
    detects when their coexistence needed an explicit decision that was
    never made, exactly the gap that carve-out leaves open (concrete
    instance: T-1614 auditing every `frob:waive` while a sibling
    runs-last ticket in the same milestone retargets waivers underneath
    it)."""
    groups = _group_runs_last_by_milestone(root, queue)
    violations: list[Violation] = []
    for milestone, tickets in groups.items():
        ordered_tickets = sorted(tickets, key=lambda t: t.id)
        for i, a in enumerate(ordered_tickets):
            for b in ordered_tickets[i + 1 :]:
                violation = _mile004_pair_violation(milestone, a, b)
                if violation is not None:
                    violations.append(violation)
    return tuple(violations)


# frob:ticket T-2576
# frob:ticket T-2579
# frob:doc docs/modules/tickets-data-storage.md#mile003-t-2576-m2
# frob:tests tests/test_gates_milestone.py::TestMile003.test_fires_on_open_ticket_with_no_resolvable_milestone  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_once_stamped  # noqa: E501
def milestone_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """MILE003 + MILE004: the T-2576 M2 / T-2579 M4b milestone gate
    family. MILE001/MILE002 (blocking semantics over the milestone
    ordering) are M5, explicitly out of this ticket's scope."""
    return _mile003_unresolved_milestone(root, queue) + _mile004_unordered_runs_last(
        root, queue
    )


__all__ = ["milestone_gate"]
