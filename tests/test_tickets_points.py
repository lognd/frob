"""Tests for T-5132: ticket sizing (points field, `frob ticket points`
setter, start-time unsized refusal, points-weighted flow/sprint reporting)
(docs/modules/tickets-data-storage.md#points-t-5132)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner._lifecycle import _refuse_unsized_on_start, _start
from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
    set_points,
    set_tokens,
    set_unsized_ack,
)
from frob.tickets._flow import _ticket_points_per_hour, _ticket_tokens_per_point
from frob.tickets._models import POINTS_ALLOWED, validate_points


def _init_repo(tmp_path: Path, *, scope: tuple[str, ...] = ("src/m.py",)) -> str:
    """Shared git-init + `new_ticket` fixture, same shape T-2394's own
    `test_tickets_no_scope.py::_init_repo` established."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    spec = TicketSpec(
        title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN, scope=scope
    )
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestValidatePoints:
    """`validate_points`: refuse anything outside 1 2 3 5 8 13."""

    def test_valid_value_accepted(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_points kind="unit"
        for n in POINTS_ALLOWED:
            result = validate_points(n)
            assert result.is_ok
            assert result.danger_ok == n

    def test_invalid_value_refused(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_points kind="unit"
        result = validate_points(4)
        assert result.is_err
        assert result.danger_err is TicketError.InvalidPoints


class TestSetPoints:
    """`set_points`: the `frob ticket points <id> <value>` library
    entrypoint."""

    def test_valid_value_sets_field(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_points kind="unit"
        ticket_id = _init_repo(tmp_path)
        result = set_points(tmp_path, ticket_id, 5)
        assert result.is_ok
        assert result.danger_ok.points == 5

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].points == 5

    def test_invalid_value_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_points kind="unit"
        ticket_id = _init_repo(tmp_path)
        result = set_points(tmp_path, ticket_id, 4)
        assert result.is_err
        assert result.danger_err is TicketError.InvalidPoints


class TestSetUnsizedAck:
    """`set_unsized_ack`: the `--unsized-ack REASON` start-time escape
    hatch's underlying writer."""

    def test_ack_sets_both_fields(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_unsized_ack kind="unit"
        ticket_id = _init_repo(tmp_path)
        result = set_unsized_ack(tmp_path, ticket_id, "spike, size after")
        assert result.is_ok
        assert result.danger_ok.unsized_ack is True
        assert result.danger_ok.unsized_ack_reason == "spike, size after"

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_unsized_ack kind="unit"
        ticket_id = _init_repo(tmp_path)
        result = set_unsized_ack(tmp_path, ticket_id, "   ")
        assert result.is_err
        assert result.danger_err is TicketError.UnsizedAckReasonMissing


class TestSetTokens:
    """`set_tokens`: the manual token-spend recorder (T-5132 amendment)."""

    def test_sets_fields(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_setters.py::set_tokens kind="unit"
        ticket_id = _init_repo(tmp_path)
        result = set_tokens(
            tmp_path, ticket_id, tokens_in=1000, tokens_out=200, tokens_cache_read=50
        )
        assert result.is_ok
        assert result.danger_ok.tokens_in == 1000
        assert result.danger_ok.tokens_out == 200
        assert result.danger_ok.tokens_cache_read == 50


class TestStartUnsizedRefusal:
    """`_refuse_unsized_on_start`/`_start`: points required to WORK a
    ticket is the whole point of T-5132."""

    def test_unsized_queued_ticket_refuses(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_refuse_unsized_on_start kind="unit"
        ticket_id = _init_repo(tmp_path)
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.points is None
        try:
            _refuse_unsized_on_start(ticket)
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError("expected SystemExit for an unsized ticket")

    def test_sized_ticket_starts_cleanly(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_refuse_unsized_on_start kind="unit"
        ticket_id = _init_repo(tmp_path)
        set_points(tmp_path, ticket_id, 3)
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        _refuse_unsized_on_start(ticket)  # must not raise

    def test_unsized_ack_bypasses_refusal(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_apply_unsized_ack_on_start \
        # kind="unit"
        ticket_id = _init_repo(tmp_path)
        cfg = AppConfig(
            ticket_command="start",
            ticket_id=ticket_id,
            ticket_path=tmp_path,
            ticket_unsized_ack="spike, size after",
        )
        _start(tmp_path, cfg)  # must not raise

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.state.value == "in-progress"
        assert ticket.unsized_ack is True

    def test_full_start_cli_refuses_on_unsized_ticket(self, tmp_path: Path) -> None:
        # frob:tests \
        # src/frob/app/ticket_runner/_lifecycle.py::_refuse_unsized_on_start kind="unit"
        ticket_id = _init_repo(tmp_path)
        cfg = AppConfig(
            ticket_command="start", ticket_id=ticket_id, ticket_path=tmp_path
        )
        try:
            _start(tmp_path, cfg)
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError("expected SystemExit for an unsized ticket")

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].state.value != "in-progress"


class TestTicketPointsPerHour:
    """`_ticket_points_per_hour`: points/actual-hour calibration."""

    def test_unsized_or_unstarted_ticket_excluded(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_flow.py::_ticket_points_per_hour kind="unit"
        ticket_id = _init_repo(tmp_path)
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        all_tickets = dict(reloaded.danger_ok.tickets)
        # no first_done entry at all -- never started/closed
        rate, sample = _ticket_points_per_hour(tmp_path, all_tickets, {})
        assert rate is None
        assert sample == 0
        assert ticket_id in all_tickets  # sanity: the fixture ticket exists


class TestTicketTokensPerPoint:
    """`_ticket_tokens_per_point`: tokens/point calibration (T-5132
    amendment)."""

    def test_sized_and_tokened_calibrates(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_flow.py::_ticket_tokens_per_point kind="unit"
        ticket_id = _init_repo(tmp_path)
        set_points(tmp_path, ticket_id, 5)
        set_tokens(tmp_path, ticket_id, tokens_in=8000, tokens_out=2000)
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        rate = _ticket_tokens_per_point(dict(reloaded.danger_ok.tickets))
        assert rate == 2000.0  # (8000 + 2000) / 5

    def test_no_qualifying_ticket_returns_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_flow.py::_ticket_tokens_per_point kind="unit"
        _init_repo(tmp_path)
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        rate = _ticket_tokens_per_point(dict(reloaded.danger_ok.tickets))
        assert rate is None


class TestSprintViewPoints:
    """`sprint_view`'s T-5132 points rollup."""

    def test_points_rollup_and_eta(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_flow.py::sprint_view kind="unit"
        from frob.tickets import set_sprint, sprint_view

        ticket_id = _init_repo(tmp_path)
        set_points(tmp_path, ticket_id, 5)
        set_sprint(tmp_path, ticket_id, "kernel-decoupling")
        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        report = sprint_view(reloaded.danger_ok, "kernel-decoupling")
        assert report.total_points == 5
        assert report.points_done == 0
        assert report.sized_count == 1
        # not done yet -> no ETA (nothing observed as done)
        assert report.points_eta_days is None
