"""Tests for T-2393's `frob ticket close --no-behavior-change` front door:
writing the pre-existing `frob:no-behavior-change reason="..."` BUG002
remedy (T-1616) through the validated `set_body` mutation path (T-2392)
instead of a hand-edit of `tickets/T-####/ticket.md`
(docs/modules/tickets-data-storage.md#frob-ticket-body-t-2392)."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from frob.__main__ import _build_parser
from frob.app.config import AppConfig
from frob.app.ticket_runner._close_cmd import _apply_no_behavior_change_directive
from frob.gates._bug_repro import (
    _BugReproOutcome,
    _no_behavior_change_reason,
    bug_repro_violations,
)
from frob.tickets import Origin, TicketKind, TicketSpec, load_active, new_ticket
from frob.tickets._models import Ticket, TicketState


def _init_repo(tmp_path: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    spec = TicketSpec(title="a ticket", kind=TicketKind.SECURITY, origin=Origin.HUMAN)
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestNoBehaviorChangeCli:
    """`_apply_no_behavior_change_directive`: the CLI-layer function
    `frob ticket close --no-behavior-change` runs before BUG002's own
    check (T-2393)."""

    def test_flag_writes_directive_before_close(self, tmp_path: Path) -> None:
        """`--no-behavior-change --no-behavior-change-reason TEXT` appends
        a `frob:no-behavior-change reason="TEXT"` line to the ticket body,
        parseable by BUG002's own `_no_behavior_change_reason` -- an
        end-to-end round trip through the real writer AND the real
        reader, not a hand-built fixture body."""
        ticket_id = _init_repo(tmp_path)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_close_no_behavior_change=True,
            ticket_close_no_behavior_change_reason="epic rollup, no runtime delta",
        )
        _apply_no_behavior_change_directive(tmp_path, cfg)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert "frob:no-behavior-change" in ticket.body
        assert _no_behavior_change_reason(ticket) == "epic rollup, no runtime delta"
        # the write went through set_body's accountable path -- an audit
        # entry must exist, not a silent body edit
        assert len(ticket.body_changes) == 1
        assert ticket.body_changes[0].mode == "append"

    def test_reason_missing_exits_nonzero(self, tmp_path: Path) -> None:
        """`--no-behavior-change` with NO reason given exits nonzero
        rather than writing an unreasoned/empty directive -- the positive
        control proving this front door cannot become a silent escape
        hatch (mirrors T-2353/T-2392's own mandatory-reason discipline)."""
        ticket_id = _init_repo(tmp_path)
        cfg = AppConfig(
            ticket_command="close",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_close_no_behavior_change=True,
        )
        with pytest.raises(SystemExit) as exc_info:
            _apply_no_behavior_change_directive(tmp_path, cfg)
        assert exc_info.value.code != 0

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].body_changes == ()

    def test_flag_absent_is_a_no_op(self, tmp_path: Path) -> None:
        """Without `--no-behavior-change`, the function does nothing --
        an ordinary `frob ticket close` must not be affected by this
        ticket's changes at all."""
        ticket_id = _init_repo(tmp_path)
        cfg = AppConfig(
            ticket_command="close", ticket_id=ticket_id, ticket_path=tmp_path
        )
        _apply_no_behavior_change_directive(tmp_path, cfg)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].body_changes == ()


def _bug_ticket(*, body: str) -> Ticket:
    return Ticket(
        id="T-0900",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=("m.py",),
        evidence=("tests/test_x.py::test_x",),
        attachments=(),
        body=body,
    )


class TestRealArgvParsing:
    """Regression guard (T-1927/T-2387's own live-fire incident class,
    and this very series' own T-2392/T-2393 friction while it was still
    unwired): parse real argv through the real parser and real
    `AppConfig.from_args`, not a hand-built `AppConfig` -- the only way
    to catch a field silently dropped by `_config_external.py`'s
    allowlists rather than genuinely forwarded."""

    def test_close_no_behavior_change_flags_survive_real_argv_parsing(self) -> None:
        parser = _build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "close",
                "T-1234",
                "--no-behavior-change",
                "--no-behavior-change-reason",
                "doc only",
            ]
        )
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_close_no_behavior_change is True
        assert cfg.ticket_close_no_behavior_change_reason == "doc only"

    def test_body_append_flags_survive_real_argv_parsing(self) -> None:
        parser = _build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "body",
                "T-1234",
                "--append",
                "a directive",
                "--reason",
                "why",
            ]
        )
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_body_append == "a directive"
        assert cfg.ticket_body_reason == "why"


class TestGateNotWeakened:
    """POSITIVE CONTROL (T-2393's own second acceptance criterion): a
    ticket with genuinely confirmatory-only evidence and NO
    `--no-behavior-change` flag/directive must still be refused by
    BUG002 -- proving this ticket's front door did not touch the gate's
    own enforcement, only how the pre-existing escape hatch is reached."""

    def test_confirmatory_only_without_directive_still_refused(
        self, tmp_path: Path
    ) -> None:
        # a plain bug-kind ticket, no frob:no-behavior-change anywhere in
        # its body -- the ordinary case BUG002 must keep catching
        ticket = _bug_ticket(body="## Description\nordinary bug fix\n")
        with patch(
            "frob.gates._bug_repro._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.PASSED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].rule == "BUG002"
        assert violations[0].severity == "error"

    def test_directive_present_inverts_to_must_still_pass(self, tmp_path: Path) -> None:
        """Once the directive IS present (as `--no-behavior-change` would
        write it), BUG002's obligation correctly inverts: PASSED_AT_PARENT
        is fine, FAILED_AT_PARENT is now the violation -- confirming this
        ticket's front door reaches the SAME pre-existing T-1616 code
        path, not a new/separate one."""
        body = (
            '## Description\nx\nfrob:no-behavior-change reason="doc only, no '
            'behavioral delta"\n'
        )
        ticket = _bug_ticket(body=body)
        with patch(
            "frob.gates._bug_repro._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.PASSED_AT_PARENT,
        ):
            assert bug_repro_violations(tmp_path, ticket, "main") == ()
        with patch(
            "frob.gates._bug_repro._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.FAILED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert "no-behavior-change" in violations[0].message
