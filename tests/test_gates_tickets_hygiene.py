"""T-0409: TICK003 ledger-hygiene gate -- warn (then error past a hard cap)
when the active tickets.md ledger holds too many closed (done/dropped)
tickets un-archived."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import Origin, TicketKind, TicketQueue, TicketState
from frob.tickets._models import Ticket
from frob.tickets._store import write_ticket


def _closeable_ticket(ticket_id: str, state: TicketState) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"{ticket_id} ticket",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        body="## Description\nsomething\n",
    )


def _seed_closed(root: Path, count: int, *, dropped: int = 0, offset: int = 0) -> None:
    for i in range(count):
        state = TicketState.DROPPED if i < dropped else TicketState.DONE
        write_ticket(root, _closeable_ticket(f"T-{offset + i:04d}", state))


def _empty_queue() -> TicketQueue:
    return TicketQueue(tickets={})


class TestTick003StaleArchive:
    def test_below_warn_threshold_is_clean(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_below_warn_threshold_is_clean  # noqa: E501
        _seed_closed(tmp_path, 5)
        violations = tickets_gate(tmp_path, _empty_queue())
        assert not any(v.rule == "TICK003" for v in violations)

    def test_above_default_warn_threshold_warns(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_above_default_warn_threshold_warns  # noqa: E501
        # T-1750: default warn moved 20 -> 10 (fire earlier, so archive
        # housekeeping is schedulable well before it becomes urgent).
        _seed_closed(tmp_path, 11, dropped=3)
        violations = [
            v for v in tickets_gate(tmp_path, _empty_queue()) if v.rule == "TICK003"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN
        assert "11 closed ticket" in violations[0].message
        assert "frob ticket archive" in violations[0].message

    def test_above_default_error_threshold_errors(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_above_default_error_threshold_errors  # noqa: E501
        # T-1750: default error moved 60 -> 400 -- far above anything a
        # real drive organically reaches, so TICK003 can no longer force
        # `frob ticket archive` to run at an unsafe, non-quiet moment
        # (docs/modules/tickets-data-storage.md#archive-the-live-worktree-guard-t-1750).
        # The hard ERROR tier still exists as a backstop for a genuinely
        # neglected ledger.
        _seed_closed(tmp_path, 401)
        violations = [
            v for v in tickets_gate(tmp_path, _empty_queue()) if v.rule == "TICK003"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_open_tickets_never_count_toward_threshold(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_open_tickets_never_count_toward_threshold  # noqa: E501
        for i in range(100):
            write_ticket(tmp_path, _closeable_ticket(f"T-{i:04d}", TicketState.QUEUED))
        violations = tickets_gate(tmp_path, _empty_queue())
        assert not any(v.rule == "TICK003" for v in violations)

    def test_configurable_thresholds_from_frob_toml(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_configurable_thresholds_from_frob_toml  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[tickets]\nstale_archive_warn = 2\nstale_archive_error = 4\n"
        )
        _seed_closed(tmp_path, 3)
        violations = [
            v for v in tickets_gate(tmp_path, _empty_queue()) if v.rule == "TICK003"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN

        _seed_closed(tmp_path, 2, offset=3)  # brings total closed to 5, past error=4
        violations = [
            v for v in tickets_gate(tmp_path, _empty_queue()) if v.rule == "TICK003"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_malformed_frob_toml_degrades_to_defaults(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_malformed_frob_toml_degrades_to_defaults  # noqa: E501
        (tmp_path / "frob.toml").write_text("not valid toml [[[")
        _seed_closed(tmp_path, 5)
        # Must not raise; default warn=10 (T-1750) means 5 closed tickets
        # is clean.
        violations = tickets_gate(tmp_path, _empty_queue())
        assert not any(v.rule == "TICK003" for v in violations)

    def test_never_writes_or_archives_anything(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive.test_never_writes_or_archives_anything  # noqa: E501
        """Resurrection-safety by construction (T-0409): the gate only
        counts, it never touches tickets-archive.md."""
        _seed_closed(tmp_path, 61)
        tickets_gate(tmp_path, _empty_queue())
        assert not (tmp_path / "tickets-archive.md").exists()
