"""Tests for T-0938's history-derived sprint velocity/burndown
(`frob.tickets.sprint_velocity`) -- mined from `tickets.md`'s own git
log rather than a separate tracked counter (docs/modules/tickets.md#public-api).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from frob.tickets import (
    Ticket,
    TicketQueue,
    TicketState,
    sprint_velocity,
    ticket_flow,
)
from frob.tickets._models import SprintTransition, SprintVelocityReport
from frob.tickets._store import write_ticket
from tests.test_tickets_tiers import _ticket


def _commit(tmp_path: Path, message: str) -> None:
    """Stage+commit `tickets.md` in `tmp_path`'s git checkout with a fixed
    test identity, so `sprint_velocity`'s git-log mining has real,
    reproducible history to walk."""
    subprocess.run(["git", "add", "tickets.md"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=tmp_path,
        check=True,
    )


# frob:ticket T-1100
# frob:ticket T-1151
def _commit_on(tmp_path: Path, message: str, day: date) -> None:
    """Same as `_commit`, but pins both author/committer date to `day`
    (midday UTC) via `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` -- `ticket_flow`
    date-buckets `_mine_done_transitions`'s REAL commit timestamps (unlike
    `sprint_velocity`, which only counts transitions, never buckets them
    by day), so a `ticket_flow` test needs deterministic commit dates, not
    whatever the real wall-clock happens to be when the test runs."""
    import os

    iso = f"{day.isoformat()}T12:00:00+00:00"
    env = {**os.environ, "GIT_AUTHOR_DATE": iso, "GIT_COMMITTER_DATE": iso}
    subprocess.run(["git", "add", "tickets.md"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=tmp_path,
        check=True,
        env=env,
    )


# frob:ticket T-0938
# frob:ticket T-1151
class TestModelsAreFrozen:
    """`SprintTransition`/`SprintVelocityReport` are `frozen=True` (T-0938,
    same immutability contract as every other report model in this
    module) -- these tests exist specifically to kill the `frozen=True`
    -> `frozen=False` mutants TEST016 flagged as confirmatory-only
    (neither model was otherwise exercised for mutation past
    construction)."""

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_sprint_transition_rejects_field_assignment(self) -> None:
        # frob:tests src/frob/tickets/_models.py::SprintTransition kind="unit"
        transition = SprintTransition(
            ticket_id="T-0001",
            sha="a" * 40,
            committed_at=datetime.now(UTC),
            from_state="in-progress",
            to_state="done",
        )
        with pytest.raises(ValidationError):
            transition.to_state = "queued"  # type: ignore[misc]

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_sprint_velocity_report_rejects_field_assignment(self) -> None:
        # frob:tests src/frob/tickets/_models.py::SprintVelocityReport kind="unit"
        report = SprintVelocityReport(sprint="sprint-1")
        with pytest.raises(ValidationError):
            report.closed = 5  # type: ignore[misc]


# frob:ticket T-0938
# frob:ticket T-1151
class TestSprintVelocity:
    """`sprint_velocity` mines `done` transitions from `tickets.md`'s git
    history for whichever tickets currently carry a given `sprint` label
    -- distinct from `sprint_view.closed`'s current-state snapshot."""

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_transitions_mined_from_history(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::sprint_velocity kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        queued = _ticket(
            ticket_id="T-0001", state=TicketState.QUEUED, sprint="sprint-1"
        )
        write_ticket(tmp_path, queued)
        _commit(tmp_path, "queue T-0001")

        in_progress = queued.model_copy(update={"state": TicketState.IN_PROGRESS})
        write_ticket(tmp_path, in_progress)
        _commit(tmp_path, "start T-0001")

        done = in_progress.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done)
        _commit(tmp_path, "close T-0001")

        queue = TicketQueue(tickets={done.id: done})
        report = sprint_velocity(tmp_path, queue, "sprint-1")

        assert report.sprint == "sprint-1"
        assert report.total == 1
        assert report.closed == 1
        assert report.remaining == 0
        assert len(report.transitions) == 1
        transition = report.transitions[0]
        assert transition.ticket_id == "T-0001"
        assert transition.from_state == "in-progress"
        assert transition.to_state == "done"

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_reopen_and_reclose_both_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::sprint_velocity kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        ticket = _ticket(
            ticket_id="T-0002", state=TicketState.IN_PROGRESS, sprint="sprint-2"
        )
        write_ticket(tmp_path, ticket)
        _commit(tmp_path, "start T-0002")

        done_once = ticket.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done_once)
        _commit(tmp_path, "close T-0002")

        reopened = done_once.model_copy(update={"state": TicketState.IN_PROGRESS})
        write_ticket(tmp_path, reopened)
        _commit(tmp_path, "reopen T-0002")

        done_again = reopened.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done_again)
        _commit(tmp_path, "reclose T-0002")

        queue = TicketQueue(tickets={done_again.id: done_again})
        report = sprint_velocity(tmp_path, queue, "sprint-2")

        assert len(report.transitions) == 2
        assert report.closed == 2

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_no_tickets_in_sprint_is_empty_not_a_crash(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::sprint_velocity kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        queue = TicketQueue(tickets={})
        report = sprint_velocity(tmp_path, queue, "sprint-none")
        assert report.transitions == ()
        assert report.closed == 0
        assert report.total == 0
        assert report.remaining == 0

    # frob:ticket T-0938
    # frob:ticket T-1151
    def test_non_git_root_returns_empty_transitions(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::sprint_velocity kind="unit"
        ticket: Ticket = _ticket(
            ticket_id="T-0003", state=TicketState.DONE, sprint="sprint-3"
        )
        queue = TicketQueue(tickets={ticket.id: ticket})
        report = sprint_velocity(tmp_path, queue, "sprint-3")
        assert report.transitions == ()
        assert report.closed == 0
        assert report.remaining == 0
        assert report.total == 1


# frob:ticket T-1528
# frob:ticket T-1100
# frob:ticket T-1151
class TestTicketFlow:
    """`ticket_flow` (T-1100): filed/day (from `created`) vs landed/day
    (mined the same way `sprint_velocity` is, over the WHOLE queue) vs
    net, plus a naive burn-down ETA. Uses `_commit_on` (fixed
    `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`) throughout, not the plain
    `_commit` `TestSprintVelocity` uses -- `ticket_flow` date-buckets the
    real commit timestamp, so a deterministic date is required, unlike
    `sprint_velocity` which only counts transitions."""

    # frob:ticket T-1100
    # frob:ticket T-1151
    def test_filed_and_landed_counted_per_day(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::ticket_flow kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        the_day = date(2026, 6, 1)
        ticket = _ticket(ticket_id="T-0001", state=TicketState.QUEUED, created=the_day)
        write_ticket(tmp_path, ticket)
        _commit_on(tmp_path, "queue T-0001", the_day)

        in_progress = ticket.model_copy(update={"state": TicketState.IN_PROGRESS})
        write_ticket(tmp_path, in_progress)
        _commit_on(tmp_path, "start T-0001", the_day)

        done = in_progress.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done)
        _commit_on(tmp_path, "close T-0001", the_day)

        queue = TicketQueue(tickets={done.id: done})
        report = ticket_flow(tmp_path, queue, today=the_day)

        assert len(report.rows) == 1
        row = report.rows[0]
        assert row.day == the_day
        assert row.filed == 1
        assert row.landed == 1
        assert row.net == 0

    # frob:ticket T-1100
    # frob:ticket T-1151
    def test_zero_activity_days_are_filled_not_sparse(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::ticket_flow kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        filed_day = date(2026, 6, 1)
        ticket = _ticket(
            ticket_id="T-0001", state=TicketState.QUEUED, created=filed_day
        )
        write_ticket(tmp_path, ticket)
        _commit_on(tmp_path, "queue T-0001", filed_day)

        queue = TicketQueue(tickets={ticket.id: ticket})
        report = ticket_flow(tmp_path, queue, today=date(2026, 6, 4))

        assert [r.day for r in report.rows] == [
            date(2026, 6, 1),
            date(2026, 6, 2),
            date(2026, 6, 3),
            date(2026, 6, 4),
        ]
        assert report.rows[1].filed == 0
        assert report.rows[1].landed == 0

    # frob:ticket T-1100
    # frob:ticket T-1151
    def test_eta_none_when_queue_not_shrinking(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::ticket_flow kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

        ticket = _ticket(
            ticket_id="T-0001",
            state=TicketState.QUEUED,
            created=date(2026, 6, 1),
        )
        queue = TicketQueue(tickets={ticket.id: ticket})
        report = ticket_flow(tmp_path, queue, today=date(2026, 6, 1))

        assert report.trailing_net_rate >= 0
        assert report.eta_days is None

    # frob:ticket T-1100
    # frob:ticket T-1151
    def test_eta_computed_when_queue_shrinking(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::ticket_flow kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        # Every ticket was FILED 5 days before `today` (so `today`'s own
        # trailing window sees zero new filings) and LANDED exactly on
        # `today` (3 done-transitions) -- a clean net=-3 on the one day
        # that matters, unambiguously shrinking the queue.
        filed_day = date(2026, 5, 27)
        today = date(2026, 6, 1)
        for i in range(3):
            tid = f"T-000{i + 1}"
            started = _ticket(
                ticket_id=tid, state=TicketState.IN_PROGRESS, created=filed_day
            )
            write_ticket(tmp_path, started)
            _commit_on(tmp_path, f"start {tid}", filed_day)
            done = started.model_copy(update={"state": TicketState.DONE})
            write_ticket(tmp_path, done)
            _commit_on(tmp_path, f"close {tid}", today)

        open_ticket = _ticket(
            ticket_id="T-0099", state=TicketState.QUEUED, created=filed_day
        )
        write_ticket(tmp_path, open_ticket)
        _commit_on(tmp_path, "queue T-0099", filed_day)

        # Reload the queue from the ledger itself so every landed id is
        # actually present with its real (now DONE) state, matching
        # `ticket_flow`'s real caller (`frob ticket flow` loads the current
        # ledger, not a hand-built snapshot).
        from frob.tickets import load_active

        queue = load_active(tmp_path).danger_ok

        report = ticket_flow(tmp_path, queue, today=today)
        assert report.trailing_net_rate < 0
        assert report.eta_days is not None

    # frob:ticket T-1528
    def test_median_cycle_days_from_created_to_first_done(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::ticket_flow kind="unit"
        # frob:tests src/frob/tickets/_setters.py::_median_cycle_days kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        filed_day = date(2026, 5, 27)
        today = date(2026, 6, 1)
        # two tickets: cycles of 5 and 3 days -> median 4.0
        for i, close_day in enumerate((today, date(2026, 5, 30))):
            tid = f"T-000{i + 1}"
            started = _ticket(
                ticket_id=tid, state=TicketState.IN_PROGRESS, created=filed_day
            )
            write_ticket(tmp_path, started)
            _commit_on(tmp_path, f"start {tid}", filed_day)
            done = started.model_copy(update={"state": TicketState.DONE})
            write_ticket(tmp_path, done)
            _commit_on(tmp_path, f"close {tid}", close_day)
        from frob.tickets import load_active

        queue = load_active(tmp_path).danger_ok
        report = ticket_flow(tmp_path, queue, today=today)
        assert report.median_cycle_days == 4.0

    # frob:ticket T-1528
    def test_median_cycle_none_when_nothing_done(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::_median_cycle_days kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        open_ticket = _ticket(
            ticket_id="T-0001", state=TicketState.QUEUED, created=date(2026, 5, 27)
        )
        write_ticket(tmp_path, open_ticket)
        _commit_on(tmp_path, "queue T-0001", date(2026, 5, 27))
        from frob.tickets import load_active

        queue = load_active(tmp_path).danger_ok
        report = ticket_flow(tmp_path, queue, today=date(2026, 6, 1))
        assert report.median_cycle_days is None

    # frob:ticket T-1142
    def test_archived_ticket_still_counts_toward_landed(self, tmp_path: Path) -> None:
        """T-1142 (the exact incident): a ticket that has since been moved
        out of tickets.md into tickets-archive.md by `frob ticket archive`
        must still show up in `landed` for the day it actually landed --
        its done-transition commit is still readable in tickets.md's own
        git history (from before the archive-sweep commit removed it),
        `_mine_done_transitions` just needs to be asked to look for it."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        the_day = date(2026, 7, 26)
        ticket = _ticket(ticket_id="T-0001", state=TicketState.QUEUED, created=the_day)
        write_ticket(tmp_path, ticket)
        _commit_on(tmp_path, "queue T-0001", the_day)

        in_progress = ticket.model_copy(update={"state": TicketState.IN_PROGRESS})
        write_ticket(tmp_path, in_progress)
        _commit_on(tmp_path, "start T-0001", the_day)

        done = in_progress.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done)
        _commit_on(tmp_path, "close T-0001", the_day)

        # Archive sweep: T-0001 leaves tickets.md entirely (an empty
        # active ledger) and lands in tickets-archive.md instead -- the
        # exact shape a real `frob ticket archive` produces.
        from frob.tickets._store import (
            _LEDGER_HEADER,
            archive_path,
            ledger_path,
            write_archive,
        )

        assert write_archive(tmp_path, {done.id: done}).is_ok
        ledger_path(tmp_path).write_text(_LEDGER_HEADER, encoding="utf-8")
        _commit_on(tmp_path, "archive T-0001", date(2026, 7, 27))

        assert archive_path(tmp_path).is_file()

        # `queue` is the ACTIVE-only view (matches the real CLI's
        # load_active) and no longer contains T-0001 at all.
        empty_queue = TicketQueue(tickets={})
        report = ticket_flow(tmp_path, empty_queue, today=date(2026, 7, 27))

        landed_days = {r.day: r.landed for r in report.rows}
        assert landed_days.get(the_day, 0) == 1

    # frob:ticket T-1142
    def test_archived_ticket_still_counts_toward_filed(self, tmp_path: Path) -> None:
        """The same undercount applies to `filed` -- an archived ticket's
        `created` date must still contribute, even though `queue` (the
        active-only view) no longer holds it."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )

        filed_day = date(2026, 7, 20)
        done = _ticket(ticket_id="T-0002", state=TicketState.DONE, created=filed_day)

        from frob.tickets._store import write_archive

        assert write_archive(tmp_path, {done.id: done}).is_ok

        empty_queue = TicketQueue(tickets={})
        report = ticket_flow(tmp_path, empty_queue, today=filed_day)

        filed_days = {r.day: r.filed for r in report.rows}
        assert filed_days.get(filed_day, 0) == 1
