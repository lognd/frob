"""T-0716: `frob ticket list`/`show` must OVERLAY live cross-worktree lease
state onto the ledger's own view, not write through to it (writing a
worktree's view into main's ledger is the T-0633/T-0682 corruption class).
`display_state` is the single decoration function both consume -- these
tests exercise it directly against `frob.tickets._leases._LeaseRecord`
fixtures rather than real `git worktree add` checkouts, since the decision
under test (decorate vs. not) only depends on `read_all_leases`' already-
tested stale-vs-live judgment (T-0473/T-0476), not on git plumbing.
"""
# frob:waive SCOPE001 reason="T-0716's declared scope (src/frob/tickets/**, docs/modules/tickets.md) is source-only; this new test file lives at the repo tests/ root by this repo's existing test layout, same out-of-scope-test-file shape SCOPE001 already waives elsewhere for this ticket's CLI wiring in src/frob/app/ticket_runner.py"  # noqa: E501

from __future__ import annotations

from datetime import date
from pathlib import Path

import frob.tickets as tickets_mod
from frob.tickets import (
    Origin,
    Ticket,
    TicketKind,
    TicketState,
    display_state,
)
from frob.tickets._leases import _LeaseRecord


# frob:ticket T-0716
def _ticket(*, ticket_id: str, state: TicketState = TicketState.QUEUED) -> Ticket:
    """A minimal ticket fixture for `display_state` decoration checks."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


# frob:ticket T-0716
def _lease(ticket_id: str, worktree: Path) -> _LeaseRecord:
    """A `_LeaseRecord` fixture pointing at `worktree` for `ticket_id`."""
    return _LeaseRecord(
        ticket_id=ticket_id,
        scope=(),
        worktree=str(worktree),
        branch="worktree-agent-xyz",
        recorded_at="2026-07-22T00:00:00+00:00",
    )


# frob:ticket T-0716
class TestDisplayState:
    """T-0716: `display_state` decorates a queued/planned ticket with a
    live lease, and only that case."""

    # frob:ticket T-0716
    def test_queued_with_live_lease_decorated(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_live_l\
        # ease_decorated
        worktree = tmp_path / "worktrees" / "agent-xyz"
        worktree.mkdir(parents=True)
        ticket = _ticket(ticket_id="T-9001", state=TicketState.QUEUED)
        monkeypatch.setattr(
            tickets_mod,
            "read_all_leases",
            lambda root: (_lease("T-9001", worktree),),
        )
        assert display_state(ticket, tmp_path) == "in-progress@agent-xyz"

    # frob:ticket T-0716
    def test_queued_with_stale_lease_undecorated(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_stale_\
        # lease_undecorated
        # `read_all_leases` itself already drops leases whose worktree
        # path is gone (T-0473/T-0476) -- a stale lease is simply never
        # returned, so `display_state` sees an empty tuple and falls back
        # to the plain ledger state.
        ticket = _ticket(ticket_id="T-9002", state=TicketState.QUEUED)
        monkeypatch.setattr(tickets_mod, "read_all_leases", lambda root: ())
        assert display_state(ticket, tmp_path) == "queued"

    # frob:ticket T-0716
    def test_ledger_in_progress_undecorated(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_tickets_lease_overlay.py::TestDisplayState.test_ledger_in_progress\
        # _undecorated
        worktree = tmp_path / "worktrees" / "agent-xyz"
        worktree.mkdir(parents=True)
        ticket = _ticket(ticket_id="T-9003", state=TicketState.IN_PROGRESS)
        monkeypatch.setattr(
            tickets_mod,
            "read_all_leases",
            lambda root: (_lease("T-9003", worktree),),
        )
        assert display_state(ticket, tmp_path) == "in-progress"

    # frob:ticket T-0716
    def test_no_root_never_decorates(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_tickets_lease_overlay.py::TestDisplayState.test_no_root_never_deco\
        # rates
        worktree = tmp_path / "worktrees" / "agent-xyz"
        worktree.mkdir(parents=True)
        ticket = _ticket(ticket_id="T-9004", state=TicketState.QUEUED)
        monkeypatch.setattr(
            tickets_mod,
            "read_all_leases",
            lambda root: (_lease("T-9004", worktree),),
        )
        assert display_state(ticket, None) == "queued"
