"""Tests for T-2394: an empty ticket scope is caught only at land time --
refused at `frob ticket start` instead, with a declared-no-scope escape
hatch distinguishable from mere omission
(docs/modules/tickets-lifecycle.md#declared-no-scope-t-2394)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._lifecycle import _refuse_empty_scope_on_start, _start
from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
    set_no_scope_declared,
)
from frob.tickets._new_renumber import _warn_empty_scope_on_new


def _init_repo(tmp_path: Path, *, scope: tuple[str, ...] = ()) -> str:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    spec = TicketSpec(
        title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN, scope=scope
    )
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestSetNoScopeDeclared:
    """`set_no_scope_declared`: the mutate-in-place escape hatch."""

    def test_sets_both_fields(self, tmp_path: Path) -> None:
        ticket_id = _init_repo(tmp_path)
        result = set_no_scope_declared(tmp_path, ticket_id, "pure decision record")
        assert result.is_ok
        assert result.danger_ok.no_scope_declared is True
        assert result.danger_ok.no_scope_declared_reason == "pure decision record"

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.no_scope_declared is True
        assert ticket.no_scope_declared_reason == "pure decision record"

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        """POSITIVE CONTROL: a blank reason is refused -- this front door
        cannot become a silent, unaccountable escape hatch."""
        ticket_id = _init_repo(tmp_path)
        blank = set_no_scope_declared(tmp_path, ticket_id, "   ")
        assert blank.is_err
        assert blank.danger_err is TicketError.NoScopeDeclaredReasonMissing


# frob:ticket T-3081
# frob:tests \
# tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket.test_no_scope_de\
# clared_round_trips_through_new_ticket
# frob:tests \
# tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket.test_runs_last_p\
# arallel_safe_round_trips_through_new_ticket
class TestTicketSpecFieldsSurviveNewTicket:
    """T-3081: `_ticket_from_spec` (`new_ticket`'s `Ticket(...)` builder)
    must copy EVERY bool+reason escape-hatch pair `TicketSpec` declares,
    not just the ones some earlier ticket happened to wire through. This
    is a ROUND-TRIP check by design -- filing via `TicketSpec(..., X=True,
    ...)` then reloading the written ticket from disk -- because the bug
    class here is a field silently dropped between the spec and the
    `Ticket(...)` constructor call, which a check against the in-memory
    `Ticket` `new_ticket` HAPPENS to return would not catch any more
    reliably than the buggy code itself; only a real disk round-trip
    proves the write actually carried the field."""

    def test_no_scope_declared_round_trips_through_new_ticket(
        self, tmp_path: Path
    ) -> None:
        """DESIGNATED REPRO for T-3081: at the parent commit, `_ticket_
        from_spec` has no `no_scope_declared`/`no_scope_declared_reason`
        lines at all, so this reloads as `no_scope_declared=False` even
        though the caller declared it `True` at filing time -- the exact
        shape `frob ticket start`'s T-2394 guard then wrongly refuses."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a pure decision record",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            scope=(),
            no_scope_declared=True,
            no_scope_declared_reason="pure decision record, no files to scope",
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.no_scope_declared is True
        assert (
            created.danger_ok.no_scope_declared_reason
            == "pure decision record, no files to scope"
        )

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[created.danger_ok.id]
        assert ticket.no_scope_declared is True
        assert (
            ticket.no_scope_declared_reason
            == "pure decision record, no files to scope"
        )

    def test_runs_last_parallel_safe_round_trips_through_new_ticket(
        self, tmp_path: Path
    ) -> None:
        """T-3081's OWN "check for other dropped fields" finding: `Ticket
        Spec.runs_last_parallel_safe`/`runs_last_parallel_safe_reason`
        (T-2579) is dropped by `_ticket_from_spec` the identical way
        `no_scope_declared` was -- neither field appears in the `Ticket
        (...)` construction, so both are silently lost on the filing-time
        path even though `Ticket` itself carries them and the CLI mutate
        path sets them correctly."""
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True
        )
        spec = TicketSpec(
            title="a runs-last-parallel-safe ticket",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            scope=("src/m.py",),
            runs_last=True,
            runs_last_parallel_safe=True,
            runs_last_parallel_safe_reason="read-only, cannot race any sibling",
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        assert created.danger_ok.runs_last_parallel_safe is True
        assert (
            created.danger_ok.runs_last_parallel_safe_reason
            == "read-only, cannot race any sibling"
        )

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[created.danger_ok.id]
        assert ticket.runs_last_parallel_safe is True
        assert (
            ticket.runs_last_parallel_safe_reason
            == "read-only, cannot race any sibling"
        )


class TestRefuseEmptyScopeOnStart:
    """`_refuse_empty_scope_on_start`: the hard gate at `frob ticket
    start` -- the point a lease is actually needed (T-2394)."""

    def test_empty_scope_refuses(self, tmp_path: Path) -> None:
        """MUST-NOW-FIRE fixture: an undeclared empty scope refuses."""
        ticket_id = _init_repo(tmp_path, scope=())
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        with pytest.raises(SystemExit) as exc_info:
            _refuse_empty_scope_on_start(ticket)
        assert exc_info.value.code != 0

    def test_declared_no_scope_starts_cleanly(self, tmp_path: Path) -> None:
        """A ticket that DECLARED its empty scope intentional is
        distinguishable from mere omission -- it must not be refused."""
        ticket_id = _init_repo(tmp_path, scope=())
        declared = set_no_scope_declared(tmp_path, ticket_id, "epic rollup")
        assert declared.is_ok
        _refuse_empty_scope_on_start(declared.danger_ok)  # must not raise

    def test_nonempty_scope_starts_cleanly(self, tmp_path: Path) -> None:
        """MUST-STILL-PASS control: an ordinary ticket with real scope is
        completely unaffected by this ticket's change."""
        ticket_id = _init_repo(tmp_path, scope=("src/m.py",))
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        _refuse_empty_scope_on_start(ticket)  # must not raise

    def test_full_start_cli_refuses_on_empty_undeclared_scope(
        self, tmp_path: Path
    ) -> None:
        """End-to-end through the real `_start` dispatch function, not
        just the extracted guard -- proves it is actually wired in."""
        ticket_id = _init_repo(tmp_path, scope=())
        cfg = AppConfig(
            ticket_command="start", ticket_id=ticket_id, ticket_path=tmp_path
        )
        with pytest.raises(SystemExit) as exc_info:
            _start(tmp_path, cfg)
        assert exc_info.value.code != 0

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        # state must NOT have moved to in-progress -- a refused start is a
        # real refusal, not a partial transition
        assert reloaded.danger_ok.tickets[ticket_id].state.value != "in-progress"

    def test_scope_breadth_ack_does_not_satisfy_empty_scope_refusal(
        self, tmp_path: Path
    ) -> None:
        """T-2394/T-2446 merge-conflict resolution, pinned: `--scope-
        breadth-ack` (T-2446, bypasses ONLY _refuse_over_broad_scope_on_
        start) must NOT also satisfy _refuse_empty_scope_on_start -- the
        two guards address opposite failure modes (a scope too BROAD vs
        one that is EMPTY), and an empty scope is not a "broad" one. A
        ticket with an EMPTY, undeclared scope PLUS a breadth ack must
        still be refused at start through the real `_start` dispatch
        function, proving the ack cannot silently short-circuit past this
        refusal via ordering in `_start`."""
        ticket_id = _init_repo(tmp_path, scope=())
        cfg = AppConfig(
            ticket_command="start",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_scope_breadth_ack=True,
            ticket_scope_breadth_ack_reason="epic, will narrow later",
        )
        with pytest.raises(SystemExit) as exc_info:
            _start(tmp_path, cfg)
        assert exc_info.value.code != 0

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        # the ack write itself is allowed to have gone through (it is a
        # real, independent field) -- what must NOT have happened is the
        # empty-scope refusal being bypassed by it.
        assert ticket.state.value != "in-progress"

    def test_full_start_cli_succeeds_once_declared(self, tmp_path: Path) -> None:
        """End-to-end: declaring no-scope first lets the real `_start`
        dispatch through cleanly."""
        ticket_id = _init_repo(tmp_path, scope=())
        declared = set_no_scope_declared(tmp_path, ticket_id, "pure decision record")
        assert declared.is_ok
        cfg = AppConfig(
            ticket_command="start", ticket_id=ticket_id, ticket_path=tmp_path
        )
        _start(tmp_path, cfg)

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].state.value == "in-progress"


class TestWarnEmptyScopeOnNew:
    """`_warn_empty_scope_on_new`: the earliest possible signal at filing
    time -- WARN-only, never a refusal, mirroring T-2123's posture for
    the opposite (over-broad) problem."""

    def test_empty_scope_warns_at_filing_time(self, caplog) -> None:  # noqa: ANN001
        from datetime import date

        from frob.tickets._models import Ticket, TicketState

        ticket = Ticket(
            id="T-9001",
            title="x",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="",
        )
        with caplog.at_level("WARNING"):
            _warn_empty_scope_on_new(ticket)
        assert any("EMPTY scope" in rec.message for rec in caplog.records)

    def test_declared_no_scope_is_silent(self, caplog) -> None:  # noqa: ANN001
        from datetime import date

        from frob.tickets._models import Ticket, TicketState

        ticket = Ticket(
            id="T-9002",
            title="x",
            state=TicketState.QUEUED,
            kind=TicketKind.DOCS,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="",
            no_scope_declared=True,
        )
        with caplog.at_level("WARNING"):
            _warn_empty_scope_on_new(ticket)
        assert not any("EMPTY scope" in rec.message for rec in caplog.records)

    def test_nonempty_scope_is_silent(self, caplog) -> None:  # noqa: ANN001
        from datetime import date

        from frob.tickets._models import Ticket, TicketState

        ticket = Ticket(
            id="T-9003",
            title="x",
            state=TicketState.QUEUED,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=("src/m.py",),
            evidence=(),
            attachments=(),
            body="",
        )
        with caplog.at_level("WARNING"):
            _warn_empty_scope_on_new(ticket)
        assert not any("EMPTY scope" in rec.message for rec in caplog.records)


class TestScopeCliDeclareNoScope:
    """`frob ticket scope --declare-no-scope`: real argv through the real
    parser (T-2387's own precedent shape for catching a dropped flag)."""

    def test_flag_survives_real_argv_parsing(self) -> None:
        from frob.__main__ import _build_parser

        parser = _build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "scope",
                "T-1234",
                "--declare-no-scope",
                "--reason",
                "epic rollup",
            ]
        )
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_scope_declare_no_scope is True
        assert cfg.ticket_scope_reason == "epic rollup"

    def test_flag_absent_defaults_false(self) -> None:
        """MUST-STILL-PASS control: an ordinary `scope --add` call with no
        `--declare-no-scope` leaves the field at its default False."""
        from frob.__main__ import _build_parser

        parser = _build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "scope",
                "T-1234",
                "--add",
                "src/m.py",
                "--reason",
                "narrow it",
            ]
        )
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_scope_declare_no_scope is False
