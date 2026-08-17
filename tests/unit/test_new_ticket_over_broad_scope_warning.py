"""T-2123: `frob ticket new` accepts an unacknowledged over-broad scope
with no warning at all -- the coordinator measured a whole-directory glob
(`src/frob/app/ticket_runner/`) ACCEPTED at filing time, logging 614
scope-closure warnings (8 shown, 606 collapsed). T-1866 (T-2094's own
investigation) confirmed START-time enforcement already exists for this
exact breadth measure; this is the EARLIER gap -- the over-broad scope
enters the ledger and can suppress the `doable` queue's signal for other
agents from the moment of FILING, not just from start.

`_warn_over_broad_scope_on_new` extends the SAME TICK009/`large_glob_
warnings` breadth measure and `scope_breadth_ack` escape hatch T-1866
already established, to `new_ticket` -- WARN-only (a brand-new ticket has
no id yet to acknowledge against, so a hard refusal would strand the
filer), with severity that SCALES with how catastrophic the match count
is (T-2123's second finding: an 8-of-614 collapsed display made a
catastrophic scope look like a minor nit)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import load_queue
from frob.tickets._models import TicketState


# frob:ticket T-2123
class TestWarnOverBroadScopeOnNew:
    """Acceptance: a mega-glob scope warns loudly at `frob ticket new`
    filing time, an acknowledged one stays silent, and a precisely-scoped
    ticket is unaffected -- mirroring `TestTicketStart`'s own T-1866
    precedent in tests/unit/test_app_runners_batch7.py, at filing time
    instead of start time."""

    # frob:ticket T-2123
    def test_over_broad_scope_warns_at_filing_time(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew.test_over_broad_scope_warns_at_filing_time  # noqa: E501
        """(MUST FAIL FIRST on main): filing a ticket with a chronically
        over-broad literal scope glob (`src/frob/**`) must warn at FILING
        time -- fails today: `frob ticket new` accepts it with no such
        warning."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="broad scope ticket",
            ticket_kind="bug",
            ticket_scope=["src/frob/**"],
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "T-0001" in caplog.text
        assert "over-broad" in caplog.text or "narrow it" in caplog.text
        # Filing itself still succeeds -- this is advisory, not a gate.
        queue = load_queue(tmp_path).danger_ok
        assert "T-0001" in queue.tickets
        assert queue.tickets["T-0001"].state == TicketState.QUEUED

    # frob:ticket T-2123
    def test_precise_scope_is_silent_at_filing_time(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew.test_precise_scope_is_silent_at_filing_time  # noqa: E501
        """A precisely-scoped ticket (a single named file) files silently,
        as today -- this check must never fire on ordinary, correctly-
        scoped work."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="fix one file",
            ticket_kind="bug",
            ticket_scope=["src/frob/tickets/_new_renumber.py"],
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "over-broad" not in caplog.text
        assert "CATASTROPHICALLY" not in caplog.text

    # frob:ticket T-2123
    def test_ack_bypasses_the_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew.test_ack_bypasses_the_warning  # noqa: E501
        """T-1866's existing `scope_breadth_ack` escape hatch (`Ticket.
        scope_breadth_ack`, the same field `scope-ack` writes) also
        suppresses THIS warning when re-checked -- no second waiver
        mechanism invented. A brand-new filing has no id yet to
        acknowledge against (this ticket's own scope-note), so this
        exercises `_warn_over_broad_scope_on_new` directly against an
        already-acknowledged ticket, the shape a re-file/re-check would
        see."""
        from frob.tickets._new_renumber import _warn_over_broad_scope_on_new
        from frob.tickets._store import load_all, write_ticket

        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="broad scope ticket, to be acknowledged",
            ticket_kind="bug",
            ticket_scope=["src/frob/**"],
        )
        ticket_run(cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok["T-0001"]
        acked = ticket.model_copy(
            update={
                "scope_breadth_ack": True,
                "scope_breadth_ack_reason": "genuine epic umbrella",
            }
        )
        assert write_ticket(tmp_path, acked).is_ok

        caplog.clear()
        with caplog.at_level("WARNING"):
            _warn_over_broad_scope_on_new(tmp_path, acked)
        assert "over-broad" not in caplog.text
        assert "CATASTROPHICALLY" not in caplog.text

    # frob:ticket T-2123
    def test_severity_scales_with_a_catastrophic_match_count(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew.test_severity_scales_with_a_catastrophic_match_count  # noqa: E501
        """T-2123's second finding: severity/prominence scales with the
        collapsed count -- a catastrophically over-broad scope (a literal
        chronically-broad glob, an automatic full-repo match) logs at
        ERROR with an explicit 'CATASTROPHICALLY' summary line, not just
        an ordinary WARNING indistinguishable from a merely-a-bit-broad
        one."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="whole package glob ticket",
            ticket_kind="bug",
            ticket_scope=["src/frob/**"],
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert error_records, (
            f"expected at least one ERROR-level record; got:\n{caplog.text}"
        )
        assert any("CATASTROPHICALLY" in r.getMessage() for r in error_records)
