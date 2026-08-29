"""T-3087: `reopen_ticket` -- the explicit, reason-carrying, audited escape
hatch for a falsely-closed ticket. Reproduces the recovery path T-3064
needed directly against the real function (not a re-implementation).

frob:tests tests/unit/test_reopen_ticket.py::TestReopenTicket.test_reopen_requires_done
frob:tests tests/unit/test_reopen_ticket.py::TestReopenTicket.test_reopen_requires_reason
frob:tests tests/unit/test_reopen_ticket.py::TestReopenTicket.test_reopen_appends_dated_entry_and_requeues
"""  # noqa: E501

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import TicketError, TicketState, reopen_ticket


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def _write_ticket(root: Path, ticket_id: str, state, body: str) -> None:  # noqa: ANN001
    from frob.tickets import Origin, Ticket, TicketKind
    from frob.tickets._store import _serialize_ticket

    ticket = Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body=body,
        evidence=("tests/unit/test_reopen_ticket.py::TestReopenTicket",)
        if state is TicketState.DONE
        else (),
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


def _load(root: Path, ticket_id: str):  # noqa: ANN001
    from frob.tickets import _load_one

    return _load_one(root, ticket_id).danger_ok


class TestReopenTicket:
    def test_reopen_requires_done(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-9101",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\nDone.\n",
        )

        result = reopen_ticket(tmp_path, "T-9101", "wrong close")

        assert result.is_err
        assert result.danger_err is TicketError.ReopenRequiresDone
        assert _load(tmp_path, "T-9101").state is TicketState.IN_PROGRESS

    def test_reopen_requires_reason(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-9102",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\nDone.\n",
        )

        result = reopen_ticket(tmp_path, "T-9102", "   ")

        assert result.is_err
        assert result.danger_err is TicketError.ReopenReasonMissing
        assert _load(tmp_path, "T-9102").state is TicketState.DONE

    def test_reopen_appends_dated_entry_and_requeues(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-9103",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\n"
            "T-9103 is BLOCKED, not implemented.\n",
        )

        result = reopen_ticket(
            tmp_path, "T-9103", "falsely closed with an unsatisfied blocker"
        )

        assert result.is_ok
        reopened = result.danger_ok
        assert reopened.state is TicketState.QUEUED
        assert "## Reopen log" in reopened.body
        assert "falsely closed with an unsatisfied blocker" in reopened.body
        # the original Done report narrative must survive the reopen --
        # this is a recovery path, not a rewrite of the record.
        assert "T-9103 is BLOCKED, not implemented." in reopened.body

        on_disk = _load(tmp_path, "T-9103")
        assert on_disk.state is TicketState.QUEUED
        assert f"- {date.today().isoformat()}:" in on_disk.body
