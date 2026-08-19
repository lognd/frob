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
from frob.tickets import TicketQueue, TicketState

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


# frob:ticket T-2576
# frob:doc docs/modules/tickets-data-storage.md#mile003-t-2576-m2
# frob:tests tests/test_gates_milestone.py::TestMile003.test_fires_on_open_ticket_with_no_resolvable_milestone  # noqa: E501
# frob:tests tests/test_gates_milestone.py::TestMile003.test_silent_once_stamped  # noqa: E501
def milestone_gate(root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """MILE003: the T-2576 M2 milestone-resolution gate family. Currently
    a single rule -- MILE001/MILE002 (blocking semantics over the
    milestone ordering) are M5, explicitly out of this ticket's scope."""
    return _mile003_unresolved_milestone(root, queue)


__all__ = ["milestone_gate"]
