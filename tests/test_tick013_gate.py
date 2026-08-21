"""tests/test_tick013_gate.py -- TICK013 (T-2557) coverage, split into its
own file rather than tests/test_gates.py for the same reason
tests/test_tick012_gate.py is standalone: avoids any declared-scope
collision with a ticket that owns tests/test_gates.py while in-progress.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _ticket(
    *,
    ticket_id: str,
    state: TicketState,
    scope: tuple[str, ...] = (),
    no_scope_declared: bool = False,
) -> Ticket:
    """A minimal `Ticket` fixture -- mirrors
    `tests/test_tick012_gate.py::_ticket`'s own shape, kept local so this
    file has no import-time dependency on that module."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        no_scope_declared=no_scope_declared,
        no_scope_declared_reason=("epic rollup, no file scope" if no_scope_declared else None),
        body="## Description\nx\n",
    )


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit -- mirrors
    `tests/test_tick012_gate.py::_run`, kept local for the same reason
    `_ticket` is."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


class TestTick013EmptyScope:
    """TICK013 (T-2557): an IN_PROGRESS/PLANNED ticket whose declared
    scope is empty and which has not opted out via `no_scope_declared`
    holds no write lease while able to edit anything, and no other gate
    (SCOPE001 is diff-driven, TICK009 only checks breadth) tests for it."""

    def _repo(self, tmp_path: Path) -> Path:
        """A minimal real git repo at `tmp_path` -- `tickets_gate` reads
        the ledger/leases directories relative to this root."""
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        (tmp_path / "tickets.md").write_text("# Tickets\n", encoding="utf-8")
        return tmp_path

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_in_progress_empty_scope_fires  # noqa: E501
    def test_in_progress_empty_scope_fires(self, tmp_path: Path) -> None:
        """Must-fire control: an IN_PROGRESS ticket with an empty scope
        and no `no_scope_declared` opt-out -- the T-2377 incident shape."""
        root = self._repo(tmp_path)
        ticket = _ticket(ticket_id="T-2700", state=TicketState.IN_PROGRESS, scope=())
        violations = tickets_gate(root, self._queue(ticket))
        tick013 = [v for v in violations if v.rule == "TICK013"]
        assert len(tick013) == 1
        assert tick013[0].severity == Severity.ERROR
        assert "T-2700" in tick013[0].message

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_planned_empty_scope_fires  # noqa: E501
    def test_planned_empty_scope_fires(self, tmp_path: Path) -> None:
        """Must-fire control: PLANNED is treated the same as IN_PROGRESS
        (mirroring TICK009's own scan population)."""
        root = self._repo(tmp_path)
        ticket = _ticket(ticket_id="T-2701", state=TicketState.PLANNED, scope=())
        violations = tickets_gate(root, self._queue(ticket))
        assert any(v.rule == "TICK013" for v in violations)

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_declared_no_scope_is_silent  # noqa: E501
    def test_declared_no_scope_is_silent(self, tmp_path: Path) -> None:
        """Must-not-fire control: `no_scope_declared=True` is the
        first-class, justified opt-out (T-2394) -- an empty scope that
        has been explicitly disclosed is not a violation."""
        root = self._repo(tmp_path)
        ticket = _ticket(
            ticket_id="T-2702",
            state=TicketState.IN_PROGRESS,
            scope=(),
            no_scope_declared=True,
        )
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK013" for v in violations)

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_nonempty_scope_is_silent  # noqa: E501
    def test_nonempty_scope_is_silent(self, tmp_path: Path) -> None:
        """Must-not-fire control: a legitimately declared, non-empty
        scope never fires TICK013."""
        root = self._repo(tmp_path)
        ticket = _ticket(
            ticket_id="T-2703", state=TicketState.IN_PROGRESS, scope=("src/a.py",)
        )
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK013" for v in violations)

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_terminal_state_empty_scope_is_silent  # noqa: E501
    def test_terminal_state_empty_scope_is_silent(self, tmp_path: Path) -> None:
        """Must-not-fire control: a DONE ticket with an empty scope holds
        no lease at all -- terminal states are exempt entirely."""
        root = self._repo(tmp_path)
        ticket = _ticket(ticket_id="T-2704", state=TicketState.DONE, scope=())
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK013" for v in violations)

    # frob:tests tests/test_tick013_gate.py::TestTick013EmptyScope.test_queued_empty_scope_is_silent  # noqa: E501
    def test_queued_empty_scope_is_silent(self, tmp_path: Path) -> None:
        """Must-not-fire control: a QUEUED ticket's scope is a pre-work
        prediction (T-1645's own reasoning, shared with TICK009) -- not
        yet a live lease, so it is exempt like TICK009 exempts it."""
        root = self._repo(tmp_path)
        ticket = _ticket(ticket_id="T-2705", state=TicketState.QUEUED, scope=())
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK013" for v in violations)
