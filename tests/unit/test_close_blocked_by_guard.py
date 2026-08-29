"""T-3087: `_open_blockers_at_close` -- a ticket can reach `done` while
`blocked_by` still names a non-terminal ticket (measured incident: T-3064
closed done with `blocked_by=['T-3066']` and T-3066 queued). Reproduces the
close-time guard directly against the real helper (not a re-implementation).

frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_open_blocker_names_the_open_ticket_not_the_terminal_one
frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_no_blocked_by_returns_empty
frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_unresolvable_blocker_id_is_ignored
"""  # noqa: E501

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.app.ticket_runner._close_cmd import _open_blockers_at_close


def _ticket(ticket_id: str, state, *, blocked_by=()):  # noqa: ANN001
    from frob.tickets import Origin, Ticket, TicketKind

    return Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body="## Description\nx\n\n## Done report\n\nDone.\n",
        blocked_by=tuple(blocked_by),
    )


def _init_git_repo(root: Path) -> None:
    """A minimal git checkout so `load_queue`'s tickets-dir discovery has a
    real repo to work against (same helper shape as
    test_close_t1648_remainder.py's own fixture)."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def _write_ticket(
    root: Path, ticket_id: str, state, body: str, *, blocked_by=()
) -> None:  # noqa: ANN001, E501
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
        blocked_by=tuple(blocked_by),
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


class _Queue:
    def __init__(self, tickets: dict) -> None:  # noqa: ANN001
        self.tickets = tickets


class TestOpenBlockersAtClose:
    def test_open_blocker_names_the_open_ticket_not_the_terminal_one(
        self, tmp_path: Path
    ) -> None:
        from frob.tickets import TicketState

        blocked = _ticket("T-9001", TicketState.IN_PROGRESS, blocked_by=["T-9002"])
        opener = _ticket("T-9002", TicketState.QUEUED)
        queue = _Queue({"T-9001": blocked, "T-9002": opener})

        open_ids = _open_blockers_at_close(blocked, queue)

        assert open_ids == ("T-9002",)

    def test_terminal_blocker_never_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_terminal_blocker_never_refuses  # noqa: E501
        from frob.tickets import TicketState

        blocked = _ticket("T-9001", TicketState.IN_PROGRESS, blocked_by=["T-9002"])
        done_blocker = _ticket("T-9002", TicketState.DONE)
        queue = _Queue({"T-9001": blocked, "T-9002": done_blocker})

        open_ids = _open_blockers_at_close(blocked, queue)

        assert open_ids == ()

    def test_dropped_blocker_never_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_dropped_blocker_never_refuses  # noqa: E501
        from frob.tickets import TicketState

        blocked = _ticket("T-9001", TicketState.IN_PROGRESS, blocked_by=["T-9002"])
        dropped_blocker = _ticket("T-9002", TicketState.DROPPED)
        queue = _Queue({"T-9001": blocked, "T-9002": dropped_blocker})

        open_ids = _open_blockers_at_close(blocked, queue)

        assert open_ids == ()

    def test_no_blocked_by_returns_empty(self, tmp_path: Path) -> None:
        from frob.tickets import TicketState

        blocked = _ticket("T-9001", TicketState.IN_PROGRESS)
        queue = _Queue({"T-9001": blocked})

        assert _open_blockers_at_close(blocked, queue) == ()

    def test_unresolvable_blocker_id_is_ignored(self, tmp_path: Path) -> None:
        from frob.tickets import TicketState

        blocked = _ticket("T-9001", TicketState.IN_PROGRESS, blocked_by=["T-9999"])
        queue = _Queue({"T-9001": blocked})

        assert _open_blockers_at_close(blocked, queue) == ()

    def test_archived_terminal_blocker_resolves_via_load_queue(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose.test_archived_terminal_blocker_resolves_via_load_queue  # noqa: E501
        #
        # Coordinator measurement on T-3087 (sweep of the whole active
        # ledger for the T-3064 shape): a blocker that has reached a
        # terminal state gets ARCHIVED out of `tickets/`, so a naive
        # active-only lookup cannot tell "blocker archived done" apart
        # from "blocker id does not exist" -- both read as `None`. The
        # real fix is that `_close()` resolves blockers through
        # `load_queue`, which merges active + archive (`_load_merged`),
        # not a bespoke active-only lookup this test would otherwise be
        # exercising against a fake. This test goes through the REAL
        # `load_queue` against a real archived ticket file to prove the
        # merge, not just `_open_blockers_at_close`'s own dict handling.
        from frob.tickets import TicketState, load_queue
        from frob.tickets._archive import archive

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-9001",
            TicketState.IN_PROGRESS,
            "## Description\nx\n\n## Done report\n\nDone.\n",
            blocked_by=["T-9002"],
        )
        _write_ticket(
            tmp_path,
            "T-9002",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\nDone.\n",
        )
        # Move T-9002 out of the active tree into tickets-archive.md, the
        # same real move a done ticket eventually gets in this repo --
        # `_open_blockers_at_close` must resolve it there, not just while
        # it still sits in `tickets/`.
        archived = archive(tmp_path)
        assert archived.is_ok

        queue_result = load_queue(tmp_path)
        assert queue_result.is_ok
        blocked = queue_result.danger_ok.tickets["T-9001"]

        assert _open_blockers_at_close(blocked, queue_result.danger_ok) == ()
