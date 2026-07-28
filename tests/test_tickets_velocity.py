"""Tests for T-0938's history-derived sprint velocity/burndown
(`frob.tickets.sprint_velocity`) -- mined from `tickets.md`'s own git
log rather than a separate tracked counter (docs/modules/tickets.md#public-api).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from frob.tickets import Ticket, TicketQueue, TicketState, sprint_velocity
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


# frob:ticket T-0938
class TestModelsAreFrozen:
    """`SprintTransition`/`SprintVelocityReport` are `frozen=True` (T-0938,
    same immutability contract as every other report model in this
    module) -- these tests exist specifically to kill the `frozen=True`
    -> `frozen=False` mutants TEST016 flagged as confirmatory-only
    (neither model was otherwise exercised for mutation past
    construction)."""

    # frob:ticket T-0938
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
    def test_sprint_velocity_report_rejects_field_assignment(self) -> None:
        # frob:tests src/frob/tickets/_models.py::SprintVelocityReport kind="unit"
        report = SprintVelocityReport(sprint="sprint-1")
        with pytest.raises(ValidationError):
            report.closed = 5  # type: ignore[misc]


# frob:ticket T-0938
class TestSprintVelocity:
    """`sprint_velocity` mines `done` transitions from `tickets.md`'s git
    history for whichever tickets currently carry a given `sprint` label
    -- distinct from `sprint_view.closed`'s current-state snapshot."""

    # frob:ticket T-0938
    def test_transitions_mined_from_history(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_velocity kind="unit"
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
    def test_reopen_and_reclose_both_counted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_velocity kind="unit"
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
    def test_no_tickets_in_sprint_is_empty_not_a_crash(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_velocity kind="unit"
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        queue = TicketQueue(tickets={})
        report = sprint_velocity(tmp_path, queue, "sprint-none")
        assert report.transitions == ()
        assert report.closed == 0
        assert report.total == 0
        assert report.remaining == 0

    # frob:ticket T-0938
    def test_non_git_root_returns_empty_transitions(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/__init__.py::sprint_velocity kind="unit"
        ticket: Ticket = _ticket(
            ticket_id="T-0003", state=TicketState.DONE, sprint="sprint-3"
        )
        queue = TicketQueue(tickets={ticket.id: ticket})
        report = sprint_velocity(tmp_path, queue, "sprint-3")
        assert report.transitions == ()
        assert report.closed == 0
        assert report.remaining == 0
        assert report.total == 1
