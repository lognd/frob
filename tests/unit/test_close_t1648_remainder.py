"""T-1648: `_undisclosed_remainder_reason` -- a ticket closes with
disclosed unfinished work only if a `Filed:` line names a real, open
follow-up ticket. Reproduces the T-1420/T-1204 incident shape directly
against the real helper (not a re-implementation)."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.app.ticket_runner._close_cmd import _undisclosed_remainder_reason


def _init_git_repo(root: Path) -> None:
    """A minimal git checkout so `load_queue`'s tickets-dir discovery and
    any git-touching machinery this helper's callees rely on has a real
    repo to work against."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
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
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


class TestRemainderDisclosureGuard:
    def test_clean_narrative_is_unaffected(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_clean_narrative_is_unaffected  # noqa: E501
        from frob.tickets import TicketState

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\nFixed everything, all clean.\n",
        )
        ticket = _load(tmp_path, "T-0900")
        assert _undisclosed_remainder_reason(tmp_path, ticket) is None

    def test_refuses_when_disclosure_language_has_no_filed_ticket(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_refuses_when_disclosure_language_has_no_filed_ticket  # noqa: E501
        from frob.tickets import TicketState

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\n"
            "Split 1 file; 52 more remain not attempted.\n",
        )
        ticket = _load(tmp_path, "T-0900")
        reason = _undisclosed_remainder_reason(tmp_path, ticket)
        assert reason is not None
        assert "not attempted" in reason

    def test_allows_when_filed_ticket_is_open(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_allows_when_filed_ticket_is_open  # noqa: E501
        from frob.tickets import TicketState

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\n"
            "Split 1 file; 52 more remain not attempted.\n\nFiled: T-0901\n",
        )
        _write_ticket(tmp_path, "T-0901", TicketState.QUEUED, "## Description\ny\n")
        ticket = _load(tmp_path, "T-0900")
        assert _undisclosed_remainder_reason(tmp_path, ticket) is None

    def test_refuses_when_filed_ticket_is_already_closed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard.test_refuses_when_filed_ticket_is_already_closed  # noqa: E501
        from frob.tickets import TicketState

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\n"
            "Split 1 file; 52 more remain not attempted.\n\nFiled: T-0901\n",
        )
        _write_ticket(tmp_path, "T-0901", TicketState.DONE, "## Description\ny\n")
        ticket = _load(tmp_path, "T-0900")
        reason = _undisclosed_remainder_reason(tmp_path, ticket)
        assert reason is not None
        assert "T-0901" in reason


def _load(root: Path, ticket_id: str):  # noqa: ANN001, ANN202
    from frob.tickets import load_queue

    result = load_queue(root)
    assert result.is_ok, result.err
    return result.danger_ok.tickets[ticket_id]
