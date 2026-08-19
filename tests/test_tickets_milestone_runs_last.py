"""Tests for T-2578 (M4): `runs_last` rescoped to the ticket's own
EFFECTIVE milestone, instead of the whole ledger (docs/modules/
tickets-data-storage.md, `frob.tickets._doable._other_open_tickets`).
"""

from __future__ import annotations

from datetime import date

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
    doable,
)


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    created: date = date(2026, 1, 1),
    runs_last: bool = False,
    milestone: str | None = None,
    parent: str | None = None,
) -> Ticket:
    """Build a minimal leaf `Ticket` fixture, matching the shape
    `tests/test_tickets_priority.py::_ticket` already uses, extended with
    a `milestone` field for this ticket's scoping tests."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        priority=priority,
        blocked_by=(),
        parent=parent,
        tier=TicketTier.TICKET,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
        runs_last=runs_last,
        milestone=milestone,
    )


class TestRunsLastMilestoneScoping:
    """T-2578: a `runs_last` ticket's "other open tickets" count is scoped
    to its own effective milestone, not the whole ledger."""

    def test_unmilestoned_runs_last_keeps_global_semantics(self) -> None:
        """Back-compat control: a `runs_last` ticket with NO milestone
        anywhere in its chain stays blocked by ANY other open ticket,
        repo-wide -- unchanged from pre-T-2578 behavior."""
        last = _ticket(ticket_id="T-9001", runs_last=True)
        other = _ticket(ticket_id="T-9002", milestone="1.0.0")
        queue = TicketQueue(tickets={last.id: last, other.id: other})
        result = doable(queue)
        assert last.id not in {t.id for t in result}

    def test_unmilestoned_runs_last_becomes_doable_once_all_else_terminal(
        self,
    ) -> None:
        """Same fixture as above, but the other ticket is now terminal --
        the unmilestoned runs-last ticket must become doable, proving the
        back-compat path is not just "always blocked"."""
        last = _ticket(ticket_id="T-9001", runs_last=True)
        other = _ticket(ticket_id="T-9002", state=TicketState.DONE, milestone="1.0.0")
        queue = TicketQueue(tickets={last.id: last, other.id: other})
        result = doable(queue)
        assert last.id in {t.id for t in result}

    def test_milestoned_runs_last_blocked_by_same_milestone_open_work(
        self,
    ) -> None:
        """A runs-last ticket in milestone 1.0.0 with OTHER open 1.0.0 work
        must NOT be doable (the milestone's own work is not done yet)."""
        last = _ticket(ticket_id="T-9101", runs_last=True, milestone="1.0.0")
        other = _ticket(ticket_id="T-9102", milestone="1.0.0")
        queue = TicketQueue(tickets={last.id: last, other.id: other})
        result = doable(queue)
        assert last.id not in {t.id for t in result}

    def test_milestoned_runs_last_doable_once_same_milestone_work_terminal(
        self,
    ) -> None:
        """Same fixture, but the 1.0.0 sibling is now DONE -- the
        runs-last ticket must become doable: this is the M4 scoping
        change in action."""
        last = _ticket(ticket_id="T-9101", runs_last=True, milestone="1.0.0")
        other = _ticket(ticket_id="T-9102", state=TicketState.DONE, milestone="1.0.0")
        queue = TicketQueue(tickets={last.id: last, other.id: other})
        result = doable(queue)
        assert last.id in {t.id for t in result}

    def test_milestoned_runs_last_not_blocked_by_other_milestone_open_work(
        self,
    ) -> None:
        """Scoping proof: open work in a DIFFERENT milestone (2.0.0) must
        never block a runs-last ticket declared in 1.0.0 -- the whole
        point of M4 is that "last" means last-in-THIS-milestone, not
        last-in-the-repo."""
        last = _ticket(ticket_id="T-9101", runs_last=True, milestone="1.0.0")
        other_milestone = _ticket(ticket_id="T-9201", milestone="2.0.0")
        queue = TicketQueue(tickets={last.id: last, other_milestone.id: other_milestone})
        result = doable(queue)
        assert last.id in {t.id for t in result}

    def test_runs_last_sibling_carve_out_preserved_within_a_milestone(
        self,
    ) -> None:
        """The pre-existing T-1613 sibling carve-out must survive M4's
        rescope: two runs-last tickets sharing ONE milestone must not
        mutually deadlock -- each is doable once every non-runs-last
        ticket in that same milestone is terminal, regardless of the
        other runs-last sibling's own state."""
        last_a = _ticket(ticket_id="T-9301", runs_last=True, milestone="1.0.0")
        last_b = _ticket(ticket_id="T-9302", runs_last=True, milestone="1.0.0")
        queue = TicketQueue(tickets={last_a.id: last_a, last_b.id: last_b})
        result = doable(queue)
        ids = {t.id for t in result}
        assert last_a.id in ids
        assert last_b.id in ids
