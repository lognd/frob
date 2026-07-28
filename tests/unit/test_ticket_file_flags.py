"""`frob ticket new --body-file`/`--acceptance-file` and `frob ticket scope
--reason-file` (T-0737): file-input variants that keep long/backticked
ticket prose off the shell entirely, mirroring `done-report --why-file`."""
# frob:ticket T-0737

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _new, _scope
from frob.tickets import Origin, Ticket, TicketKind, load_queue, new_ticket
from frob.tickets._models import TicketSpec


# frob:ticket T-0737
def _make_ticket(tmp_path: Path, *, scope: tuple[str, ...]) -> Ticket:
    """Seed a single queued ticket with the given scope, for `_scope` tests
    that need an existing ticket to mutate (mirrors
    tests/test_tickets_scope_mutation.py's own `_make_ticket` fixture)."""
    spec = TicketSpec(
        title="seed",
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        scope=scope,
    )
    result = new_ticket(tmp_path, spec)
    return result.danger_ok


# frob:ticket T-0737
class TestNewBodyFile:
    """`frob ticket new --body-file PATH` (T-0737)."""

    # frob:ticket T-0737
    def test_body_file_round_trips_byte_exact(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewBodyFile.test_body_file_round_trips_byte_exact  # noqa: E501
        body_path = tmp_path / "body.txt"
        # No leading/trailing newline: the ledger writer (_ledger.py)
        # strips outer `\n` from a ticket body regardless of source, so a
        # byte-exact round trip is only meaningful on the content the
        # ledger actually preserves verbatim -- interior backticks, quotes,
        # and dollar signs (T-0737's actual hazard).
        raw = 'has backticks `cmd here` and quotes "yo" and dollars $HOME and $(sub)'
        body_path.write_text(raw, encoding="utf-8")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="byte exact body",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body_file=body_path,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.body == raw

    # frob:ticket T-0737
    def test_body_and_body_file_together_errors_cleanly(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewBodyFile.test_body_and_body_file_together_errors_cleanly  # noqa: E501
        body_path = tmp_path / "body.txt"
        body_path.write_text("file body", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="conflicting body",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body="inline body",
            ticket_body_file=body_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            _new(tmp_path, cfg)
        assert exc_info.value.code == 1

    # frob:ticket T-0737
    def test_unreadable_body_file_errors_cleanly(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewBodyFile.test_unreadable_body_file_errors_cleanly  # noqa: E501
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="missing file",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body_file=tmp_path / "does-not-exist.txt",
        )
        with pytest.raises(SystemExit) as exc_info:
            _new(tmp_path, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-0737
class TestNewAcceptanceFile:
    """`frob ticket new --acceptance-file PATH` (T-0737)."""

    # frob:ticket T-0737
    def test_blank_line_separated_blocks_become_criteria(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile.test_blank_line_separated_blocks_become_criteria  # noqa: E501
        acc_path = tmp_path / "acceptance.txt"
        acc_path.write_text(
            "GIVEN a WHEN b THEN c\n\nGIVEN d WHEN e THEN f\n", encoding="utf-8"
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="acceptance from file",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_acceptance_file=acc_path,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert [c.text for c in ticket.acceptance] == [
            "GIVEN a WHEN b THEN c",
            "GIVEN d WHEN e THEN f",
        ]

    # frob:ticket T-0737
    def test_one_per_line_when_no_blank_lines(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile.test_one_per_line_when_no_blank_lines  # noqa: E501
        acc_path = tmp_path / "acceptance.txt"
        acc_path.write_text("first criterion\nsecond criterion\n", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="one per line",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_acceptance_file=acc_path,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert [c.text for c in ticket.acceptance] == [
            "first criterion",
            "second criterion",
        ]

    # frob:ticket T-0737
    def test_acceptance_and_acceptance_file_together_errors_cleanly(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile.test_acceptance_and_acceptance_file_together_errors_cleanly  # noqa: E501
        acc_path = tmp_path / "acceptance.txt"
        acc_path.write_text("from file", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="conflicting acceptance",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_acceptance=["inline criterion"],
            ticket_acceptance_file=acc_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            _new(tmp_path, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-0737
class TestScopeReasonFile:
    """`frob ticket scope <id> --reason-file PATH` (T-0737)."""

    # frob:ticket T-0737
    def test_reason_file_round_trips_byte_exact(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestScopeReasonFile.test_reason_file_round_trips_byte_exact  # noqa: E501
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        reason_path = tmp_path / "reason.txt"
        raw = "needs `backtick-cmd` and $DOLLAR because of scope drift"
        reason_path.write_text(raw, encoding="utf-8")
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/__main__.py"],
            ticket_scope_reason_file=reason_path,
        )
        _scope(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        mutated = queue.tickets[ticket.id]
        assert "src/frob/__main__.py" in mutated.scope
        assert mutated.scope_changes[-1].reason == raw

    # frob:ticket T-0737
    def test_reason_and_reason_file_together_errors_cleanly(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestScopeReasonFile.test_reason_and_reason_file_together_errors_cleanly  # noqa: E501
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        reason_path = tmp_path / "reason.txt"
        reason_path.write_text("file reason", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/__main__.py"],
            ticket_scope_reason="inline reason",
            ticket_scope_reason_file=reason_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            _scope(tmp_path, cfg)
        assert exc_info.value.code == 1

    # frob:ticket T-0737
    def test_neither_reason_nor_reason_file_errors_cleanly(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_file_flags.py::TestScopeReasonFile.test_neither_reason_nor_reason_file_errors_cleanly  # noqa: E501
        ticket = _make_ticket(tmp_path, scope=("src/frob/other/**",))
        cfg = AppConfig(
            ticket_command="scope",
            ticket_id=ticket.id,
            ticket_path=tmp_path,
            ticket_scope_add=["src/frob/__main__.py"],
        )
        with pytest.raises(SystemExit) as exc_info:
            _scope(tmp_path, cfg)
        assert exc_info.value.code == 1
