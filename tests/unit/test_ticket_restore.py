"""T-2954: `frob ticket restore <id> --reason TEXT` -- the repair verb for
a ticket stranded under `tickets/archive/` in a NON-terminal state
(T-0450's own live incident: `state: queued` sitting under
`tickets/archive/T-0450/`, 37 days stale, with no CLI primitive able to
find it -- `frob ticket drop` resolves ids via the active store only).

Real git fixture repos throughout, matching `tests/unit/
test_close_promote_drafts.py`'s own self-contained style."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.app.ticket_runner._archive import _restore
from frob.tickets import Origin, TicketError, TicketKind, TicketState, restore


@pytest.fixture(autouse=True)
def _no_ambient_worktree_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    """`restore`'s `enforce_worktree_lease` call refuses outright whenever
    the recording/dispatching agent's own shell happens to have
    `FROB_WORKTREE` set to a DIFFERENT path (T-0884's own precedent,
    reused verbatim from `test_close_promote_drafts.py`'s identical
    fixture) -- clearing it here makes this module immune to that
    ambient env."""
    monkeypatch.delenv("FROB_WORKTREE", raising=False)
    monkeypatch.delenv("FROB_AGENT", raising=False)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init boilerplate already duplicated \
# verbatim across many land/ticket test modules -- see \
# tests/unit/test_close_promote_drafts.py's own identical waiver for the same rationale"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="fixture-repo git-commit boilerplate already duplicated \
# verbatim across many land/ticket test modules -- see \
# tests/unit/test_close_promote_drafts.py's own identical waiver for the same rationale"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _write_v2_archived_ticket(
    root: Path,
    ticket_id: str,
    *,
    state: TicketState,
    body: str = "## Description\nx\n",
    attachment_path: str | None = None,
) -> Path:
    """Write `ticket_id`'s `ticket.md` directly under `tickets/archive/
    <id>/` -- v2-mode's archived shape, bypassing `archive()` itself so a
    NON-terminal archived state (T-0450's own anomaly) can be constructed
    directly, the same way the ticket's own body describes it having
    happened (by some means outside `archive`, which structurally never
    selects a non-terminal ticket to move)."""
    from frob.tickets._models import Attachment, Ticket
    from frob.tickets._store import _serialize_ticket

    attachments: tuple[Attachment, ...] = ()
    if attachment_path is not None:
        attachments = (
            Attachment(path=attachment_path, caption="note", sha256="0" * 64),
        )
    ticket = Ticket(
        id=ticket_id,
        title="sample stranded ticket",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 7, 20),
        body=body,
        attachments=attachments,
    )
    archive_dir = root / "tickets" / "archive" / ticket_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "ticket.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )
    return archive_dir


class TestRestore:
    """`frob.tickets.restore` -- the core git-mv-back primitive."""

    def test_restores_a_non_terminal_archived_ticket_to_active(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestore.test_restores_a_non_terminal_a\
        # rchived_ticket_to_active
        """T-0450's own exact incident shape: a `queued` ticket stranded
        under `tickets/archive/` moves back into the active store, its
        state left untouched (restore repairs a LOCATION invariant, not a
        state one)."""
        from frob.tickets import TicketState, load_active
        from frob.tickets._store import v2_archive_dir, v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        _write_v2_archived_ticket(root, "T-0450", state=TicketState.QUEUED)
        _commit_all(root, "seed stranded T-0450")

        result = restore(root, "T-0450", reason="T-2954 repair: hand-edit residue")
        assert result.is_ok, result.err
        restored = result.danger_ok
        assert restored.state is TicketState.QUEUED
        assert "T-2954 repair: hand-edit residue" in restored.body
        assert "## Restore log" in restored.body

        assert not v2_archive_dir(root, "T-0450").exists()
        assert v2_ticket_dir(root, "T-0450").exists()

        active = load_active(root)
        assert active.is_ok, active.err
        assert "T-0450" in active.danger_ok.tickets
        assert active.danger_ok.tickets["T-0450"].state is TicketState.QUEUED

    def test_restore_reverses_the_t2986_attachment_path_rewrite(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestore.test_restore_reverses_the_t298\
        # 6_attachment_path_rewrite
        """A restored ticket's archive-prefixed attachment path
        (`archive/<id>/attachments/...`, the shape `_rewrite_moved_
        attachment_paths` -- T-2986 -- leaves behind on ARCHIVE) must read
        the plain `<id>/attachments/...` form again once active, or
        COV004 stops resolving it the moment it is back in the active
        tree."""
        from frob.tickets import TicketState

        root = tmp_path / "repo"
        _git_init(root)
        _write_v2_archived_ticket(
            root,
            "T-0451",
            state=TicketState.QUEUED,
            attachment_path="archive/T-0451/attachments/01-note.txt",
        )
        _commit_all(root, "seed stranded T-0451 with attachment")

        result = restore(root, "T-0451", reason="repair")
        assert result.is_ok, result.err
        restored = result.danger_ok
        assert restored.attachments[0].path == "T-0451/attachments/01-note.txt"

    def test_refuses_when_not_archived(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestore.test_refuses_when_not_archived
        root = tmp_path / "repo"
        _git_init(root)
        (root / "README.md").write_text("empty repo\n", encoding="utf-8")
        _commit_all(root, "empty repo")

        result = restore(root, "T-9999", reason="repair")
        assert result.is_err
        assert result.danger_err is TicketError.RestoreNotArchived

    def test_refuses_when_destination_already_exists(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestore.test_refuses_when_destination_\
        # already_exists
        """A duplicate id (archived AND active copies both present) must
        refuse loudly, never silently overwrite or merge either side --
        the same 'refuse loudly' posture this ticket's whole series is
        built around."""
        from frob.tickets._models import Ticket
        from frob.tickets._store import _serialize_ticket, v2_ticket_path

        root = tmp_path / "repo"
        _git_init(root)
        _write_v2_archived_ticket(root, "T-0452", state=TicketState.QUEUED)
        active_ticket = Ticket(
            id="T-0452",
            title="active duplicate",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            body="## Description\nactive copy\n",
        )
        active_path = v2_ticket_path(root, "T-0452")
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(_serialize_ticket(active_ticket), encoding="utf-8")
        _commit_all(root, "seed duplicate T-0452")

        result = restore(root, "T-0452", reason="repair")
        assert result.is_err
        assert result.danger_err is TicketError.RestoreDestinationExists

    def test_refuses_a_blank_reason(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestore.test_refuses_a_blank_reason
        root = tmp_path / "repo"
        _git_init(root)
        _write_v2_archived_ticket(root, "T-0453", state=TicketState.QUEUED)
        _commit_all(root, "seed T-0453")

        result = restore(root, "T-0453", reason="   ")
        assert result.is_err
        assert result.danger_err is TicketError.RestoreReasonMissing


# frob:ticket T-2954
class TestArchiveRefusesNonTerminal:
    """`_archive_v2_move_tickets`'s T-2954 defense-in-depth check: goal 2
    of T-2954's two proposed fixes -- the archive write path must refuse
    (never silently move) a non-terminal ticket. `archive`/`archive_v2`'s
    own selection filter already makes this structurally unreachable via
    the normal public entry points (the must-STAY-quiet case below), so
    this exercises the guard directly against `_archive_v2_move_tickets`,
    the one place that actually performs the `git mv`."""

    def test_refuses_a_non_terminal_ticket_reaching_the_move_loop(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal.test_refuses\
        # _a_non_terminal_ticket_reaching_the_move_loop
        """Must-FIRE: calling the move loop directly with a queued
        ticket in `to_archive` (bypassing the normal filter, simulating a
        future caller/refactor that weakens it) refuses loudly and moves
        nothing."""
        from frob.tickets._archive import _archive_v2_move_tickets
        from frob.tickets._models import Ticket
        from frob.tickets._store import (
            _serialize_ticket,
            v2_archive_dir,
            v2_ticket_path,
        )

        root = tmp_path / "repo"
        _git_init(root)
        ticket = Ticket(
            id="T-0455",
            title="still open",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            body="## Description\nx\n",
        )
        path = v2_ticket_path(root, "T-0455")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_serialize_ticket(ticket), encoding="utf-8")
        _commit_all(root, "seed T-0455")

        result = _archive_v2_move_tickets(root, {"T-0455": ticket})
        assert result.is_err
        assert result.danger_err is TicketError.ArchiveNonTerminalTicket
        assert path.exists(), "ticket must NOT have moved"
        assert not v2_archive_dir(root, "T-0455").exists()

    def test_normal_archive_of_done_tickets_still_moves_them(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestArchiveRefusesNonTerminal.test_normal_\
        # archive_of_done_tickets_still_moves_them
        """Must-STAY-quiet: the ordinary path (a genuinely done ticket)
        is completely unaffected by T-2954's new guard -- `archive()`
        still moves it exactly as before."""
        from frob.tickets import archive
        from frob.tickets._models import Ticket
        from frob.tickets._store import _serialize_ticket, v2_archive_dir, v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        ticket = Ticket(
            id="T-0456",
            title="finished",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            evidence=("tests/test_x.py::test_ok",),
            body="## Description\nx\n\n## Done report\n\ndone\n",
        )
        path = root / "tickets" / "T-0456" / "ticket.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_serialize_ticket(ticket), encoding="utf-8")
        _commit_all(root, "seed done T-0456")

        result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1
        assert not v2_ticket_dir(root, "T-0456").exists()
        assert (v2_archive_dir(root, "T-0456") / "ticket.md").exists()


class TestRestoreCli:
    """`_restore` -- the CLI dispatch wrapper (`frob ticket restore`)."""

    def test_restore_cli_wiring_delegates_and_commits(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestoreCli.test_restore_cli_wiring_del\
        # egates_and_commits
        """The end-to-end CLI path: `_restore` calls `frob.tickets.
        restore` and commits the WHOLE multi-path change (both the
        vacated archive directory and the new active one) in one commit
        -- never leaving either half staged-but-uncommitted."""
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_active

        root = tmp_path / "repo"
        _git_init(root)
        _write_v2_archived_ticket(root, "T-0454", state=TicketState.QUEUED)
        _commit_all(root, "seed stranded T-0454")

        cfg = AppConfig(ticket_id="T-0454", ticket_reason="repair via CLI")
        _restore(root, cfg)

        active = load_active(root)
        assert active.is_ok, active.err
        assert "T-0454" in active.danger_ok.tickets

        # T-2954: only `tickets/` matters here -- `.frob/` is this
        # process's own untracked local cache dir, unrelated to whether
        # the restore's git-mv-plus-write left the LEDGER dirty.
        status = _run(["git", "status", "--porcelain", "--", "tickets"], root).stdout
        assert status.strip() == "", (
            f"restore CLI left tickets/ dirty: {status!r}"
        )

    def test_restore_exits_when_ticket_id_missing(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestoreCli.test_restore_exits_when_tic\
        # ket_id_missing
        """Kills the `ticket_id is None or not ticket_reason` -> `and`
        mutant from the ticket_id side: a reason present but no id must
        still refuse."""
        from frob.app.config import AppConfig

        cfg = AppConfig(ticket_id=None, ticket_reason="a real reason")
        with pytest.raises(SystemExit):
            _restore(tmp_path, cfg)

    def test_restore_exits_when_reason_missing(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestoreCli.test_restore_exits_when_rea\
        # son_missing
        """Kills the same mutant from the reason side: an id present but
        no --reason must still refuse."""
        from frob.app.config import AppConfig

        cfg = AppConfig(ticket_id="T-0001", ticket_reason=None)
        with pytest.raises(SystemExit):
            _restore(tmp_path, cfg)

    def test_restore_reason_flag_is_required_by_the_real_parser(self) -> None:
        # frob:tests \
        # tests/unit/test_ticket_restore.py::TestRestoreCli.test_restore_reason_flag_is\
        # _required_by_the_real_parser
        """Kills the `--reason ... required=True` -> `required=False`
        mutant directly: the REAL argparse tree (not a re-implementation)
        must refuse `frob ticket restore <id>` with no `--reason`."""
        import argparse

        from frob._cli_parsers._ticket._closeout import (
            _add_ticket_fail_evidence_archive_parsers,
        )

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="ticket_command")
        _add_ticket_fail_evidence_archive_parsers(sub)

        with pytest.raises(SystemExit):
            parser.parse_args(["restore", "T-0001"])

        # Must-stay-quiet: the SAME parser accepts a real --reason.
        parsed = parser.parse_args(["restore", "T-0001", "--reason", "why"])
        assert parsed.ticket_reason == "why"
