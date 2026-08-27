"""T-2302: `frob ticket new` had no FILING-time acknowledgement path for
a deliberately broad `--scope` -- T-2123's own `_warn_over_broad_scope_
on_new` WARN check already looks for `Ticket.scope_breadth_ack` (the
same field `frob ticket scope-ack <id>` sets after the fact) and skips
silently when it is True, but nothing let a filer set it AT filing time,
so the WARN was advisory forever.

This file proves the new `--scope-breadth-ack`/`--scope-breadth-ack-
reason` flags actually close that gap: an acknowledged broad scope files
warning-free, an unacknowledged one still warns exactly as before
(T-2123 unchanged), and `--scope-breadth-ack` with no reason is rejected
outright -- the same non-blank-reason requirement `set_scope_breadth_ack`
already enforces for the post-filing channel, now enforced at
spec-construction time too."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import load_queue
from frob.tickets._models import TicketState


# frob:ticket T-2302
class TestScopeBreadthAckFlag:
    """Acceptance: `--scope-breadth-ack --scope-breadth-ack-reason TEXT`
    at filing time silences T-2123's breadth WARN, matches on the ticket
    record itself, and a missing reason is refused."""

    # frob:ticket T-2302
    def test_acknowledged_broad_scope_is_silent_and_recorded(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests \
        # tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag\
        # .test_acknowledged_broad_scope_is_silent_and_recorded
        """(MUST FAIL FIRST on pre-T-2302 main -- the flags do not exist,
        so AppConfig construction itself fails): a broad scope filed WITH
        --scope-breadth-ack and a reason produces no over-broad warning,
        and the recorded ticket carries scope_breadth_ack=True plus the
        given reason."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="genuine epic umbrella ticket",
            ticket_kind="bug",
            ticket_scope=["src/frob/**"],
            ticket_scope_breadth_ack=True,
            ticket_scope_breadth_ack_reason="genuine epic umbrella",
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "over-broad" not in caplog.text
        assert "CATASTROPHICALLY" not in caplog.text
        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.state == TicketState.QUEUED
        assert ticket.scope_breadth_ack is True
        assert ticket.scope_breadth_ack_reason == "genuine epic umbrella"

    # frob:ticket T-2302
    def test_unacknowledged_broad_scope_still_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests \
        # tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag\
        # .test_unacknowledged_broad_scope_still_warns
        """T-2123's original filing-time WARN is unchanged for a filer
        who does not pass the new flag at all -- the default stays
        advisory-only, not silently suppressed by this ticket's change."""
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="broad scope ticket, unacknowledged",
            ticket_kind="bug",
            # T-3034: was "src/frob/**" -- over_broad_literal_globs (T-2771)
            # now derives package-prefix globs from tmp_path's OWN
            # pyproject.toml (there is none here), so "src/frob/**" no
            # longer resolves in this fixture; "tests/**" stays a
            # repo-convention literal in OVER_BROAD_LITERAL_GLOBS
            # regardless of package-name resolution, so it still exercises
            # the same WARN path this test is actually about.
            ticket_scope=["tests/**"],
        )
        with caplog.at_level("WARNING"):
            ticket_run(cfg)
        assert "over-broad" in caplog.text or "narrow it" in caplog.text
        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.scope_breadth_ack is False
        assert ticket.scope_breadth_ack_reason is None

    # frob:ticket T-2302
    def test_ack_without_reason_is_refused(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag\
        # .test_ack_without_reason_is_refused
        """`--scope-breadth-ack` with no (or a blank) reason is rejected
        by `new_ticket`'s pre-write validation gauntlet
        (`_validate_new_ticket_spec`, `TicketError.
        ScopeBreadthAckReasonMissing`) -- the same "an acknowledgement
        needs a stated reason" rule `set_scope_breadth_ack` already
        enforces for the post-filing `scope-ack` channel, now enforced
        here too. A plain function-level guard rather than a pydantic
        `TicketSpec` validator, deliberately -- see
        `_validate_new_ticket_spec`'s own docstring for why (a WIRE001/
        WAIVE008 gate inconsistency filed separately)."""
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

        for reason in (None, "   "):
            spec = TicketSpec(
                title="broad scope ticket, unreasoned ack",
                kind=TicketKind.BUG,
                origin=Origin.HUMAN,
                scope=("src/frob/**",),
                scope_breadth_ack=True,
                scope_breadth_ack_reason=reason,
            )
            result = new_ticket(tmp_path, spec, no_commit=True)
            assert result.is_err
            assert "ScopeBreadthAckReasonMissing" in str(result.danger_err)
