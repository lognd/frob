"""Tests for T-2392's `frob ticket body` verb: the validated, single-writer
front door for amending a ticket's free-text body without hand-editing
`tickets/T-####/ticket.md` (docs/modules/tickets-data-storage.md#data-models).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._mutate import _body
from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
    set_body,
)


def _init_repo(tmp_path: Path) -> str:
    """Init a throwaway git repo at `tmp_path` and file one fresh ticket,
    returning its id -- the exact warm-up `test_tickets_priority.py`'s
    `TestSetPriority` uses, applied here."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestBodyAmend:
    """`set_body` writes the ticket's body field via the ledger (T-2392)."""

    def test_append_appends_text(self, tmp_path: Path) -> None:
        """`mode="append"` on a ticket with an existing body adds the new
        text after a blank line, preserving the original body verbatim --
        round-tripped through a fresh `load_active` read, not just the
        in-memory return value."""
        ticket_id = _init_repo(tmp_path)
        first = set_body(
            tmp_path, ticket_id, "original body text", mode="set", reason="seed"
        )
        assert first.is_ok

        result = set_body(
            tmp_path,
            ticket_id,
            "frob:no-behavior-change reason=\"structural only\"",
            mode="append",
            reason="add directive found while working T-2393",
        )
        assert result.is_ok
        body = result.danger_ok.body
        assert "original body text" in body
        assert "frob:no-behavior-change" in body

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert "original body text" in reloaded.danger_ok.tickets[ticket_id].body
        assert "frob:no-behavior-change" in reloaded.danger_ok.tickets[ticket_id].body

    def test_set_replaces_text(self, tmp_path: Path) -> None:
        """`mode="set"` REPLACES the body outright -- the old text must not
        survive, unlike `append`."""
        ticket_id = _init_repo(tmp_path)
        first = set_body(tmp_path, ticket_id, "wrong body", mode="set", reason="seed")
        assert first.is_ok

        result = set_body(
            tmp_path, ticket_id, "corrected body", mode="set", reason="was wrong"
        )
        assert result.is_ok
        assert result.danger_ok.body == "corrected body"
        assert "wrong body" not in result.danger_ok.body

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        """A blank/whitespace-only `reason` is refused with
        `BodyReasonMissing` -- the positive control mirroring T-2353's
        `TriageReasonMissing` precedent: this must NOT be silently
        acceptable, or the audit trail this ticket adds is worthless."""
        ticket_id = _init_repo(tmp_path)
        blank = set_body(tmp_path, ticket_id, "text", mode="append", reason="   ")
        assert blank.is_err
        assert blank.danger_err is TicketError.BodyReasonMissing

    def test_append_records_body_change_entry(self, tmp_path: Path) -> None:
        """A successful `append` appends exactly one `BodyChangeEntry` to
        `ticket.body_changes` recording mode/reason -- the audit trail
        this ticket exists to provide, so a body amendment through the CLI
        is always distinguishable from a silent hand-edit."""
        ticket_id = _init_repo(tmp_path)
        result = set_body(
            tmp_path, ticket_id, "a directive", mode="append", reason="why I did this"
        )
        assert result.is_ok
        entries = result.danger_ok.body_changes
        assert len(entries) == 1
        assert entries[0].mode == "append"
        assert entries[0].reason == "why I did this"
        assert entries[0].new_length > entries[0].old_length

    def test_positive_control_priority_reason_still_required(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL: `set_priority`'s pre-existing T-2353 reason
        requirement is untouched by this ticket's changes -- proves
        `_set_ticket_field`'s shared reason-recording path was not
        accidentally weakened while adding `set_body` alongside it."""
        from frob.tickets import Priority, set_priority

        ticket_id = _init_repo(tmp_path)
        blank = set_priority(tmp_path, ticket_id, Priority.CRITICAL, reason="")
        assert blank.is_err
        assert blank.danger_err is TicketError.TriageReasonMissing


class TestBodyCli:
    """`frob.app.ticket_runner._mutate._body`: the thin CLI-dispatch layer
    (T-2392) that resolves `AppConfig`'s `ticket_body_*` fields and
    forwards to `set_body`. Constructs `AppConfig` directly (the
    `TestKindCliInvalidKind` precedent, `tests/test_ticket_evidence.py`)
    rather than through argparse, since this dispatch function's own
    contract is "given a populated `AppConfig`, do the right thing" --
    independent of how that `AppConfig` got populated."""

    def test_cli_append_writes_body(self, tmp_path: Path) -> None:
        """A CLI-shaped `--append TEXT --reason TEXT` call persists the
        appended text to the ticket's body."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        cfg = AppConfig(
            ticket_command="body",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_body_append="frob:no-behavior-change reason=\"doc only\"",
            ticket_body_reason="add directive via CLI",
        )
        _body(tmp_path, cfg)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert "frob:no-behavior-change" in reloaded.danger_ok.tickets[ticket_id].body

    def test_cli_missing_text_exits_nonzero(self, tmp_path: Path) -> None:
        """Neither `--append`/`--append-file`/`--set`/`--set-file` given:
        `_body` exits nonzero rather than writing an empty/no-op change --
        the positive control proving the "exactly one required" check is
        real, not dead code."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN)
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        ticket_id = created.danger_ok.id

        cfg = AppConfig(
            ticket_command="body",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_body_reason="no text given",
        )
        with pytest.raises(SystemExit) as exc_info:
            _body(tmp_path, cfg)
        assert exc_info.value.code != 0
