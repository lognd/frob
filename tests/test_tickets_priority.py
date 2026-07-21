"""Tests for T-0411's priority model: PRIORITY_RANK, doable's priority-first
ordering, set_priority, and the TICK004 queue-rot gate
(docs/modules/tickets.md#data-models)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from frob.gates import _tick004_queue_rot
from frob.tickets import (
    PRIORITY_RANK,
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    doable,
    set_priority,
)


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    created: date = date(2026, 1, 1),
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        priority=priority,
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
    )


class TestPriorityRank:
    """PRIORITY_RANK orders the four levels consistently."""

    def test_critical_outranks_low(self) -> None:
        """CRITICAL must rank strictly above LOW so `doable`'s sort key
        (`-PRIORITY_RANK[...]`) surfaces critical tickets first."""
        assert PRIORITY_RANK[Priority.CRITICAL] > PRIORITY_RANK[Priority.LOW]
        assert PRIORITY_RANK[Priority.HIGH] > PRIORITY_RANK[Priority.MEDIUM]
        assert PRIORITY_RANK[Priority.MEDIUM] > PRIORITY_RANK[Priority.LOW]


class TestDoablePriorityOrdering:
    """`doable` orders by priority first, then age, per T-0411."""

    def test_high_priority_surfaces_before_older_low_priority(self) -> None:
        """A newer HIGH ticket must precede an older LOW ticket -- the exact
        T-0177-rot scenario T-0411's Description describes."""
        old_low = _ticket(
            ticket_id="T-1001", priority=Priority.LOW, created=date(2020, 1, 1)
        )
        new_high = _ticket(
            ticket_id="T-1002", priority=Priority.HIGH, created=date(2026, 1, 1)
        )
        queue = TicketQueue(tickets={old_low.id: old_low, new_high.id: new_high})
        result = doable(queue, root=None, ignore_lease=True)
        assert [t.id for t in result] == ["T-1002", "T-1001"]

    def test_same_priority_falls_back_to_age(self) -> None:
        """Within one priority tier, ordering stays oldest-first (the
        pre-T-0411 behavior for tickets that are all the same priority)."""
        older = _ticket(ticket_id="T-2001", created=date(2020, 1, 1))
        newer = _ticket(ticket_id="T-2002", created=date(2021, 1, 1))
        queue = TicketQueue(tickets={older.id: older, newer.id: newer})
        result = doable(queue, root=None, ignore_lease=True)
        assert [t.id for t in result] == ["T-2001", "T-2002"]


class TestSetPriority:
    """`set_priority` writes the ticket's priority field via the ledger."""

    def test_updates_priority_field(self, tmp_path: Path) -> None:
        """Round-trips a priority change through `new_ticket` + `set_priority`
        + a fresh `load_active` read."""
        import subprocess

        from frob.tickets import Origin as _Origin
        from frob.tickets import TicketKind as _TicketKind
        from frob.tickets import TicketSpec, load_active, new_ticket

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        spec = TicketSpec(
            title="a ticket",
            kind=_TicketKind.BUG,
            origin=_Origin.HUMAN,
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_priority(tmp_path, ticket_id, Priority.CRITICAL)
        assert result.is_ok
        assert result.danger_ok.priority == Priority.CRITICAL

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].priority == Priority.CRITICAL


class TestTick004QueueRot:
    """TICK004: a queued/planned ticket past its priority's rot threshold."""

    def test_stale_critical_ticket_flags(self, tmp_path: Path) -> None:
        """A CRITICAL ticket created well past the default 3-day threshold
        must produce a TICK004 violation."""
        stale = _ticket(
            ticket_id="T-3001",
            priority=Priority.CRITICAL,
            created=date.today() - timedelta(days=10),
        )
        queue = TicketQueue(tickets={stale.id: stale})
        violations = _tick004_queue_rot(tmp_path, queue)
        assert any(v.rule == "TICK004" and "T-3001" in v.message for v in violations)

    def test_fresh_ticket_does_not_flag(self, tmp_path: Path) -> None:
        """A LOW ticket created today must not rot (well under any threshold)."""
        fresh = _ticket(ticket_id="T-3002", priority=Priority.LOW, created=date.today())
        queue = TicketQueue(tickets={fresh.id: fresh})
        violations = _tick004_queue_rot(tmp_path, queue)
        assert not any(v.rule == "TICK004" for v in violations)
