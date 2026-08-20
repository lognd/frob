"""T-2738: `frob ticket close` must promote pending `T-draft-*`
follow-ups the same way `frob ticket land` already does -- reproduces
the T-2718 incident directly against the real helper
(`_promote_pending_drafts_after_close`), not a re-implementation."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.app.ticket_runner._close_cmd import _promote_pending_drafts_after_close


@pytest.fixture(autouse=True)
def _no_ambient_worktree_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_promote_pending_drafts_after_close`'s `finalize_draft` calls
    mutate a REAL git repo rooted at `tmp_path` (`_init_git_repo`), which
    `frob.tickets._worktree_guard.enforce_worktree_lease` refuses outright
    whenever the recording/dispatching agent's own shell happens to have
    `FROB_WORKTREE` set to a DIFFERENT path (T-0884's own precedent:
    every genuine agent shell running this suite has it set to its
    leased worktree, not to a throwaway pytest tmp dir). Clearing it here
    makes this module immune to that ambient env, the same posture
    `_run_pytest_directly` already takes for exactly this reason."""
    monkeypatch.delenv("FROB_WORKTREE", raising=False)
    monkeypatch.delenv("FROB_AGENT", raising=False)


def _init_git_repo(root: Path) -> None:
    """A minimal git checkout so `load_queue`/`finalize_draft`'s git-
    touching machinery has a real repo to commit against."""
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
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", f"file {ticket_id}"], cwd=root, check=True
    )


class TestClosePromotesPendingDrafts:
    def test_close_promotes_a_draft_the_ticket_filed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_promotes_a_draft_the_ticket_filed  # noqa: E501
        from frob.tickets import TicketState, load_queue
        from frob.tickets._provisional import is_draft_id, mint_draft_id

        _init_git_repo(tmp_path)
        draft_id = mint_draft_id()
        assert is_draft_id(draft_id)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\nFiled: " + draft_id + "\n",
        )
        _write_ticket(
            tmp_path, draft_id, TicketState.QUEUED, "## Description\nfollow-up\n"
        )

        _promote_pending_drafts_after_close(tmp_path, "T-0900")

        queue = load_queue(tmp_path)
        assert queue.is_ok, queue.err
        tickets = queue.danger_ok.tickets
        assert draft_id not in tickets
        promoted = [tid for tid in tickets if tid not in ("T-0900", draft_id)]
        assert promoted, f"expected a promoted real id in {sorted(tickets)}"
        assert not is_draft_id(promoted[0])

    def test_close_with_no_drafts_is_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_with_no_drafts_is_unchanged  # noqa: E501
        from frob.tickets import TicketState, load_queue

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\nAll clean, nothing filed.\n",
        )
        before = load_queue(tmp_path)
        assert before.is_ok
        before_ids = set(before.danger_ok.tickets)

        _promote_pending_drafts_after_close(tmp_path, "T-0900")

        after = load_queue(tmp_path)
        assert after.is_ok
        assert set(after.danger_ok.tickets) == before_ids

    def test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted(
        self, tmp_path: Path, caplog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts.test_close_reports_and_exits_nonzero_when_a_draft_cannot_be_promoted  # noqa: E501
        import logging

        from frob.tickets import TicketState

        _init_git_repo(tmp_path)
        _write_ticket(
            tmp_path,
            "T-0900",
            TicketState.DONE,
            "## Description\nx\n\n## Done report\n\nFiled: T-draft-deadbeef\n",
        )
        # T-draft-deadbeef is referenced in the Done report but never
        # actually written as a ticket file -- load_queue succeeds (no
        # such id in the ledger) so no draft is discovered and this must
        # be a silent no-op, same as "no drafts". The genuine-failure
        # path (a draft that IS in the ledger but fails to finalize) is
        # exercised via a monkeypatched `finalize_draft` instead, since
        # provoking a real finalize failure requires corrupting internal
        # state finalize_draft itself owns.
        with caplog.at_level(logging.WARNING):
            _promote_pending_drafts_after_close(tmp_path, "T-0900")
        assert not any(r.levelno >= logging.ERROR for r in caplog.records)

        # Now the genuine-failure path: a real draft ticket in the ledger,
        # with finalize_draft patched to fail.
        from frob.tickets._provisional import mint_draft_id

        draft_id = mint_draft_id()
        _write_ticket(
            tmp_path, draft_id, TicketState.QUEUED, "## Description\nfollow-up\n"
        )

        from typani import Result
        from typani.result import Err

        import frob.app.ticket_runner._close_cmd as close_cmd
        import frob.tickets as tickets_pkg
        from frob.tickets._models import TicketError

        def _boom(root: Path, tid: str) -> Result[str, TicketError]:  # noqa: ARG001
            return Err(TicketError.NotFound)

        monkeypatch.setattr(tickets_pkg, "finalize_draft", _boom)
        with pytest.raises(SystemExit) as excinfo:
            close_cmd._promote_pending_drafts_after_close(tmp_path, "T-0900")
        assert excinfo.value.code != 0
