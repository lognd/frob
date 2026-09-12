"""T-4427: set_sprint/set_milestone must record a TriageChangeEntry with
the assignment date, so T-4424's TICK004 rot-clock restart (src/frob/
gates/_tickets_gate.py::_tick004_triage_date, landed separately, not yet
present on `main` as of this ticket -- see this ticket's Done report) has
a real date to read instead of always falling through to its fail-safe
branch (docs/modules/tickets-data-storage.md#data-models)."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
    set_milestone,
    set_sprint,
)


def _init_repo(tmp_path: Path) -> None:
    """Initialize a bare git repo with a `main` branch at `tmp_path` --
    the fixture shape `TestSetPriority` (tests/test_tickets_priority.py)
    already uses for `_setters.py` round-trip tests."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)


# frob:ticket T-4427
class TestSetSprintRecordsTriageChange:
    """`set_sprint` must append a `TriageChangeEntry` (field="sprint")
    exactly the way `set_priority`/`set_kind`/`set_component`/`set_tier`
    already do -- T-4424's TICK004 rot-clock restart reads this entry's
    `at` and had no date to read before this fix."""

    # frob:tests \
    # tests/test_tickets_triage_dates.py::TestSetSprintRecordsTriageChange.test_assigni\
    # ng_a_sprint_records_a_triage_change_entry  # noqa: E501
    def test_assigning_a_sprint_records_a_triage_change_entry(
        self, tmp_path: Path
    ) -> None:
        """A fresh sprint assignment on a never-sprinted ticket appends
        exactly one `TriageChangeEntry` with `field="sprint"`,
        `old_value=None`, the new sprint label, and `at` equal to
        today."""
        _init_repo(tmp_path)
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_sprint(tmp_path, ticket_id, "v0.531.0")
        assert result.is_ok
        entries = [c for c in result.danger_ok.triage_changes if c.field == "sprint"]
        assert len(entries) == 1
        assert entries[0].old_value is None
        assert entries[0].new_value == "v0.531.0"
        assert entries[0].at == date.today()

    # frob:tests \
    # tests/test_tickets_triage_dates.py::TestSetSprintRecordsTriageChange.test_reassig\
    # ning_the_same_sprint_still_records_an_entry  # noqa: E501
    def test_reassigning_the_same_sprint_still_records_an_entry(
        self, tmp_path: Path
    ) -> None:
        """T-2353's own contract (a no-op write with a reason still
        appends an entry, never silently swallowed): calling `set_sprint`
        twice with the SAME value appends a SECOND `TriageChangeEntry`,
        not zero."""
        _init_repo(tmp_path)
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        first = set_sprint(tmp_path, ticket_id, "v0.531.0")
        assert first.is_ok
        second = set_sprint(tmp_path, ticket_id, "v0.531.0")
        assert second.is_ok
        entries = [c for c in second.danger_ok.triage_changes if c.field == "sprint"]
        assert len(entries) == 2
        assert entries[1].old_value == "v0.531.0"
        assert entries[1].new_value == "v0.531.0"

    def test_reloaded_ticket_carries_the_recorded_entry(self, tmp_path: Path) -> None:
        """Round-trip through a fresh `load_active` read -- the entry is
        real ledger state, not just the in-memory return value."""
        _init_repo(tmp_path)
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_sprint(tmp_path, ticket_id, "v0.531.0")
        assert result.is_ok

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        entries = [
            c
            for c in reloaded.danger_ok.tickets[ticket_id].triage_changes
            if c.field == "sprint"
        ]
        assert len(entries) == 1


# frob:ticket T-4427
class TestSetMilestoneRecordsTriageChange:
    """`set_milestone` gets the identical treatment as `set_sprint` --
    T-4424's `_tick004_triage_date` reads both fields' entries."""

    # frob:tests \
    # tests/test_tickets_triage_dates.py::TestSetMilestoneRecordsTriageChange.test_assi\
    # gning_a_milestone_records_a_triage_change_entry  # noqa: E501
    def test_assigning_a_milestone_records_a_triage_change_entry(
        self, tmp_path: Path
    ) -> None:
        """A fresh milestone assignment appends exactly one
        `TriageChangeEntry` with `field="milestone"` and `at` equal to
        today."""
        _init_repo(tmp_path)
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        result = set_milestone(tmp_path, ticket_id, "1.2.0")
        assert result.is_ok
        entries = [
            c for c in result.danger_ok.triage_changes if c.field == "milestone"
        ]
        assert len(entries) == 1
        assert entries[0].old_value is None
        assert entries[0].new_value == "1.2.0"
        assert entries[0].at == date.today()


