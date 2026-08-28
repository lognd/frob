"""Tests for T-0411's priority model: PRIORITY_RANK, doable's priority-first
ordering, set_priority, and the TICK004 queue-rot gate
(docs/modules/tickets-data-storage.md#data-models)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from frob.gates import _tick004_queue_rot
from frob.tickets import (
    PRIORITY_RANK,
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketState,
    TicketTier,
    doable,
    set_priority,
)


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    created: date = date(2026, 1, 1),
    runs_last: bool = False,
    tier: TicketTier = TicketTier.TICKET,
    parent: str | None = None,
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
        parent=parent,
        tier=tier,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
        runs_last=runs_last,
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

        result = set_priority(tmp_path, ticket_id, Priority.CRITICAL, reason="test")
        assert result.is_ok
        assert result.danger_ok.priority == Priority.CRITICAL

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].priority == Priority.CRITICAL

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        """T-2353: a blank/whitespace-only `reason` is refused with
        `TriageReasonMissing` -- the positive control for the fix's own
        motivating incident (a priority change with no recorded reason)."""
        # frob:tests \
        # tests/test_tickets_priority.py::TestSetPriority.test_reason_missing_refuses
        import subprocess

        from frob.tickets import Origin as _Origin
        from frob.tickets import TicketError, TicketSpec, new_ticket
        from frob.tickets import TicketKind as _TicketKind

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=_TicketKind.BUG, origin=_Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        blank = set_priority(tmp_path, ticket_id, Priority.CRITICAL, reason="   ")
        assert blank.is_err
        assert blank.danger_err is TicketError.TriageReasonMissing

    def test_reasoned_change_records_triage_entry(self, tmp_path: Path) -> None:
        """T-2353: a reasoned priority change appends a `TriageChangeEntry`
        to `ticket.triage_changes` recording the field, old/new value,
        reason, actor, and date -- the audit trail this ticket adds."""
        # frob:tests \
        # tests/test_tickets_priority.py::TestSetPriority.test_reasoned_change_records_\
        # triage_entry
        import subprocess

        from frob.tickets import Origin as _Origin
        from frob.tickets import TicketKind as _TicketKind
        from frob.tickets import TicketSpec, new_ticket

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=_TicketKind.BUG, origin=_Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_priority(
            tmp_path, ticket_id, Priority.CRITICAL, reason="escalated for the demo"
        )
        assert result.is_ok
        entries = result.danger_ok.triage_changes
        assert len(entries) == 1
        assert entries[0].field == "priority"
        assert entries[0].old_value == "medium"
        assert entries[0].new_value == "critical"
        assert entries[0].reason == "escalated for the demo"


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

    def test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it(
        self, tmp_path: Path
    ) -> None:
        """T-2200: a rotting `runs_last` ticket (T-1614's real shape) still
        produces a TICK004 finding (age is real, disclosed information),
        but its message must NOT tell an operator to 'work it' -- `frob
        ticket start` structurally refuses any `runs_last` ticket while
        other tickets are open (`RunsLastBlocked`), so that instruction is
        an action the tool itself rejects. The must-still-pass control is
        `test_stale_critical_ticket_flags` above: an ordinary rotting
        ticket still gets the normal 'work it' message, unaffected."""
        stale = _ticket(
            ticket_id="T-1614",
            priority=Priority.HIGH,
            created=date.today() - timedelta(days=11),
            runs_last=True,
        )
        queue = TicketQueue(tickets={stale.id: stale})
        violations = _tick004_queue_rot(tmp_path, queue)
        matches = [
            v for v in violations if v.rule == "TICK004" and "T-1614" in v.message
        ]
        assert len(matches) == 1
        assert "runs_last" in matches[0].message
        assert "RunsLastBlocked" in matches[0].message
        assert "work it" not in matches[0].message

    # frob:ticket T-2229
    def test_decomposed_epic_gets_a_distinct_message_not_work_it(
        self, tmp_path: Path
    ) -> None:
        """T-2229's measured incident: T-1623 (epic, rotting) had children
        T-2223/T-2224 in-progress on main -- `parent` read as a
        STRUCTURED field off the child ticket record. The message must
        name the real state (already decomposed, being worked), never
        'work it'. Must-still-pass: `test_stale_critical_ticket_flags`
        above still gets the ordinary message for a plain leaf ticket."""
        epic = _ticket(
            ticket_id="T-1623",
            priority=Priority.CRITICAL,
            created=date.today() - timedelta(days=11),
            tier=TicketTier.EPIC,
        )
        child = _ticket(
            ticket_id="T-2223",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            created=date.today(),
            parent="T-1623",
        )
        queue = TicketQueue(tickets={epic.id: epic, child.id: child})
        violations = _tick004_queue_rot(tmp_path, queue)
        matches = [
            v for v in violations if v.rule == "TICK004" and "T-1623" in v.message
        ]
        assert len(matches) == 1
        assert "already decomposed" in matches[0].message
        assert "work it" not in matches[0].message

    # frob:ticket T-2229
    def test_undecomposed_epic_with_no_children_still_gets_work_it(
        self, tmp_path: Path
    ) -> None:
        """MUST-STILL-PASS CONTROL: an epic/story with NO children at all
        must still rot under the ordinary 'work it' message -- T-2229
        explicitly forbids silencing rot for every epic/story tier."""
        epic = _ticket(
            ticket_id="T-3003",
            priority=Priority.CRITICAL,
            created=date.today() - timedelta(days=10),
            tier=TicketTier.EPIC,
        )
        queue = TicketQueue(tickets={epic.id: epic})
        violations = _tick004_queue_rot(tmp_path, queue)
        matches = [
            v for v in violations if v.rule == "TICK004" and "T-3003" in v.message
        ]
        assert len(matches) == 1
        assert "work it" in matches[0].message

    # frob:ticket T-2229
    def test_epic_whose_only_child_is_terminal_still_gets_work_it(
        self, tmp_path: Path
    ) -> None:
        """A `done`/`dropped` child does not count as active decomposition
        -- an epic whose only child already finished (or was dropped)
        keeps the ordinary rot message, not the 'being worked' one."""
        epic = _ticket(
            ticket_id="T-3004",
            priority=Priority.CRITICAL,
            created=date.today() - timedelta(days=10),
            tier=TicketTier.EPIC,
        )
        child = _ticket(
            ticket_id="T-3005",
            state=TicketState.DONE,
            priority=Priority.HIGH,
            created=date.today(),
            parent="T-3004",
        )
        queue = TicketQueue(tickets={epic.id: epic, child.id: child})
        violations = _tick004_queue_rot(tmp_path, queue)
        matches = [
            v for v in violations if v.rule == "TICK004" and "T-3004" in v.message
        ]
        assert len(matches) == 1
        assert "work it" in matches[0].message


class TestSetPriorityLandInProgressGuard:
    """T-2785: `_set_ticket_field` (the shared home `set_priority`/
    `set_kind`/`set_tier`/`set_component`/`set_runs_last`/`set_milestone`/
    `set_sprint` all funnel through) must refuse BEFORE writing anything
    while a `frob ticket land` holds `.frob/land.lock` -- fixing this ONE
    shared function closes the same partial-write hazard
    `TestSetParentLandInProgressGuard` closes for `set_parent`'s own
    (necessarily separate, since it has its own inline write) code path,
    for every sibling setter that funnels through here at once."""

    def test_refuses_and_writes_nothing_while_land_lock_held(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard.test_refuses_and_writes_nothing_while_land_lock_held  # noqa: E501
        import fcntl
        import json
        import os as _os
        import subprocess

        from frob.tickets import Origin as _Origin
        from frob.tickets import TicketKind as _TicketKind
        from frob.tickets import TicketSpec, new_ticket
        from frob.tickets import _setters as setters_mod
        from frob.tickets._leases import LAND_LOCK_REL, LeaseError
        from frob.tickets._store import load_all

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=_TicketKind.BUG, origin=_Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id
        assert created.danger_ok.priority == Priority.MEDIUM

        lock_path = tmp_path / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = _os.open(str(lock_path), _os.O_CREAT | _os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _os.write(
            holder_fd,
            (json.dumps({"pid": _os.getpid(), "ticket_id": "T-9999"}) + "\n").encode(),
        )
        original = setters_mod.refuse_if_land_in_progress
        monkeypatch.setattr(
            setters_mod,
            "refuse_if_land_in_progress",
            lambda root, **_kw: original(root, wait_timeout_s=0),
        )
        try:
            result = set_priority(tmp_path, ticket_id, Priority.CRITICAL, reason="test")
            assert result.is_err
            assert result.danger_err == LeaseError.LandInProgress

            loaded = load_all(tmp_path)
            assert loaded.is_ok
            assert loaded.danger_ok[ticket_id].priority == Priority.MEDIUM
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            _os.close(holder_fd)
