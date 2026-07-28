"""T-0752: `frob ticket doable`'s priority column, in-flight/dispatchable
split, and undispatched-critical/high staleness alarm -- these tests
exercise the pure library functions (`has_live_lease`, `dispatch_stale_hours`,
`undispatched_stale`) directly rather than the CLI render, matching
`tests/test_tickets_lease_overlay.py`'s precedent for T-0716 (the overlay
function these build on).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import frob.tickets as tickets_mod
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketState,
    dispatch_stale_hours,
    has_live_lease,
    undispatched_stale,
)
from frob.tickets._leases import _LeaseRecord


# frob:ticket T-0752
def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    created: date = date(2026, 1, 1),
) -> Ticket:
    """A minimal ticket fixture for the staleness/lease-split checks."""
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
        body="## Description\nsomething\n",
    )


# frob:ticket T-0752
def _lease(ticket_id: str, worktree: Path) -> _LeaseRecord:
    """A `_LeaseRecord` fixture pointing at `worktree` for `ticket_id`."""
    return _LeaseRecord(
        ticket_id=ticket_id,
        scope=(),
        worktree=str(worktree),
        branch="worktree-agent-xyz",
        recorded_at="2026-07-22T00:00:00+00:00",
    )


# frob:ticket T-0752
class TestHasLiveLease:
    """`has_live_lease` -- the in-flight/dispatchable split signal."""

    # frob:ticket T-0752
    def test_queued_with_live_lease_is_in_flight(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A queued ticket a worktree already leased renders in-flight."""
        worktree = tmp_path / "wt"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: /nonexistent\n")
        monkeypatch.setattr(
            tickets_mod, "read_all_leases", lambda root: (_lease("T-0001", worktree),)
        )
        ticket = _ticket(ticket_id="T-0001", state=TicketState.QUEUED)
        assert has_live_lease(ticket, tmp_path) is True

    # frob:ticket T-0752
    def test_queued_with_no_lease_is_not_in_flight(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A plain queued ticket with no live lease is truly dispatchable."""
        monkeypatch.setattr(tickets_mod, "read_all_leases", lambda root: ())
        ticket = _ticket(ticket_id="T-0001", state=TicketState.QUEUED)
        assert has_live_lease(ticket, tmp_path) is False

    # frob:ticket T-0752
    def test_no_root_never_in_flight(self) -> None:
        """`root=None` degrades quietly, matching `display_state`."""
        ticket = _ticket(ticket_id="T-0001", state=TicketState.QUEUED)
        assert has_live_lease(ticket, None) is False


# frob:ticket T-0752
class TestDispatchStaleHours:
    """`dispatch_stale_hours` -- filing-age-in-hours measurement."""

    # frob:ticket T-0752
    def test_same_day_is_zero_hours(self) -> None:
        """A ticket filed today has sat 0h by this day-granularity measure."""
        ticket = _ticket(created=date(2026, 7, 23))
        assert dispatch_stale_hours(ticket, today=date(2026, 7, 23)) == 0.0

    # frob:ticket T-0752
    def test_one_day_old_is_24_hours(self) -> None:
        """A ticket filed exactly 1 day ago reads as 24h elapsed."""
        ticket = _ticket(created=date(2026, 7, 22))
        assert dispatch_stale_hours(ticket, today=date(2026, 7, 23)) == 24.0


# frob:ticket T-0752
class TestUndispatchedStale:
    """`undispatched_stale` -- the per-priority alarm computation."""

    # frob:ticket T-0752
    def test_critical_past_threshold_alarms(self, tmp_path: Path) -> None:
        """A critical ticket filed 2 days ago (48h) exceeds the 4h default
        critical threshold and alarms."""
        ticket = _ticket(
            ticket_id="T-0001", priority=Priority.CRITICAL, created=date(2026, 7, 21)
        )
        alarms = undispatched_stale([ticket], tmp_path, today=date(2026, 7, 23))
        assert len(alarms) == 1
        alarmed, elapsed, threshold = alarms[0]
        assert alarmed.id == "T-0001"
        assert elapsed == 48.0
        assert threshold == 4.0

    # frob:ticket T-0752
    def test_critical_under_threshold_no_alarm(self, tmp_path: Path) -> None:
        """A critical ticket filed today (0h elapsed) is under the 4h
        threshold and does not alarm."""
        ticket = _ticket(
            ticket_id="T-0001", priority=Priority.CRITICAL, created=date(2026, 7, 23)
        )
        alarms = undispatched_stale([ticket], tmp_path, today=date(2026, 7, 23))
        assert alarms == ()

    # frob:ticket T-0752
    def test_medium_priority_never_alarms(self, tmp_path: Path) -> None:
        """A medium-priority ticket has no default threshold at all, no
        matter how old -- only CRITICAL/HIGH carry a default (T-0752)."""
        ticket = _ticket(
            ticket_id="T-0001", priority=Priority.MEDIUM, created=date(2020, 1, 1)
        )
        alarms = undispatched_stale([ticket], tmp_path, today=date(2026, 7, 23))
        assert alarms == ()

    # frob:ticket T-0752
    def test_high_past_threshold_alarms(self, tmp_path: Path) -> None:
        """A high-priority ticket filed 2 days ago (48h) exceeds the 24h
        default high threshold and alarms."""
        ticket = _ticket(
            ticket_id="T-0001", priority=Priority.HIGH, created=date(2026, 7, 21)
        )
        alarms = undispatched_stale([ticket], tmp_path, today=date(2026, 7, 23))
        assert len(alarms) == 1

    # frob:ticket T-0752
    def test_configured_threshold_from_frob_toml(self, tmp_path: Path) -> None:
        """`[tickets] dispatch_stale_critical_hours` in `frob.toml` overrides
        the built-in default."""
        (tmp_path / "frob.toml").write_text(
            "[tickets]\ndispatch_stale_critical_hours = 100\n"
        )
        ticket = _ticket(
            ticket_id="T-0001", priority=Priority.CRITICAL, created=date(2026, 7, 21)
        )
        # 48h elapsed, 100h configured threshold -- must NOT alarm.
        alarms = undispatched_stale([ticket], tmp_path, today=date(2026, 7, 23))
        assert alarms == ()
