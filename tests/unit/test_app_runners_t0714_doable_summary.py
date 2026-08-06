"""T-0714: `frob ticket doable` prints at most one summary line about
scope-breadth nudges (`_render_scope_breadth_summary`), never one
`WARNING:` line per nudge per invocation -- the per-ticket detail moved
to `frob check`'s TICK009 gate (`tests/test_gates_tick009_tick010.py`)."""

# frob:ticket T-0714

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest

from frob.app import ticket_runner
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _ticket(ticket_id: str, scope: tuple[str, ...], state: TicketState) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        body="## Description\nsomething\n",
    )


def _queue(*tickets: Ticket) -> TicketQueue:
    """Small local helper: build a `TicketQueue` from loose `Ticket`s."""
    return TicketQueue(tickets={t.id: t for t in tickets})


class TestRenderScopeBreadthSummary:
    def test_no_nudges_prints_nothing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary.test_no_nudges_prints_nothing  # noqa: E501
        queue = _queue(_ticket("T-2001", ("tests/test_gates.py",), TicketState.QUEUED))
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_runner._render_scope_breadth_summary(tmp_path, queue)
        assert caplog.records == []

    def test_multiple_stale_leases_collapse_to_one_summary_line(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary.test_multiple_stale_leases_collapse_to_one_summary_line  # noqa: E501
        # T-1645: PLANNED (not QUEUED) -- these tickets have been started
        # and are the earliest state this summary (mirroring TICK009)
        # still counts.
        queue = _queue(
            *[
                _ticket(f"T-21{i:02d}", ("src/frob/**",), TicketState.PLANNED)
                for i in range(5)
            ]
        )
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_runner._render_scope_breadth_summary(tmp_path, queue)
        summary_records = [
            r for r in caplog.records if "scope-breadth nudge" in r.getMessage()
        ]
        assert len(summary_records) == 1
        assert "5 scope-breadth nudge(s)" in summary_records[0].getMessage()
        assert "frob check" in summary_records[0].getMessage()

    # frob:ticket T-1645
    def test_queued_tickets_never_contribute_a_nudge(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary.test_queued_tickets_never_contribute_a_nudge  # noqa: E501
        # T-1645: a QUEUED ticket's over-broad scope must not appear in
        # this summary at all -- matching TICK009's own exemption, so the
        # two never silently drift apart.
        queue = _queue(
            *[
                _ticket(f"T-22{i:02d}", ("src/frob/**",), TicketState.QUEUED)
                for i in range(5)
            ]
        )
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_runner._render_scope_breadth_summary(tmp_path, queue)
        assert caplog.records == []
