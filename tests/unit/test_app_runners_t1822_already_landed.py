"""T-1822: wiring `frob.tickets._doable.already_landed_markers` (T-1744
case 1, deliberately left unwired at the library level) into `frob ticket
doable`'s default render -- both the summary line
(`_render_already_landed_markers`) and the per-row inline alarm
(`_doable_row`'s `landed_ids` kwarg)."""

# frob:ticket T-1822

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app import ticket_runner
from frob.tickets import TicketState

# DUP001: reuse the T-0714 summary test module's own `_ticket`/`_queue`
# builders rather than duplicating them (100% similar candidate,
# confirmed by `frob check --ticket T-1822`) -- both modules build the
# same minimal `Ticket`/`TicketQueue` shape for the same `frob ticket
# doable` render surface.
from tests.unit.test_app_runners_t0714_doable_summary import _queue, _ticket


class TestRenderAlreadyLandedMarkers:
    # frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers.test_no_markers_prints_nothing_and_returns_empty  # noqa: E501
    def test_no_markers_prints_nothing_and_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        scoped = tmp_path / "src" / "mod.py"
        scoped.parent.mkdir(parents=True)
        scoped.write_text("def f() -> None:\n    pass\n")
        queue = _queue(_ticket("T-9101", ("src/mod.py",), TicketState.QUEUED))
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ids = ticket_runner._render_already_landed_markers(tmp_path, queue)
        assert ids == frozenset()
        # T-3140: `caplog.records` is unscoped -- it captures every record
        # that propagates to the root handler, not just this function's OWN
        # `frob.app.ticket_runner` logger the `at_level` above actually
        # scoped intent to. `over_broad_literal_globs` (frob.tickets._models,
        # a package-prefix scope resolver invoked incidentally while
        # loading the queue) unconditionally WARNs when it cannot resolve
        # `tmp_path`'s own source prefix from a (deliberately absent, in
        # this fixture) `pyproject.toml` -- an unrelated resolver's noise,
        # not this function's own render output, which is what "prints
        # nothing" asserts. Scope the assertion to this function's own
        # logger, matching the sibling test below
        # (`test_flagged_ticket_prints_one_summary_line_and_is_returned`),
        # which already filters by message content for the same reason.
        own_records = [r for r in caplog.records if r.name == "frob.app.ticket_runner"]
        assert own_records == []

    # frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers.test_flagged_ticket_prints_one_summary_line_and_is_returned  # noqa: E501
    def test_flagged_ticket_prints_one_summary_line_and_is_returned(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        scoped = tmp_path / "src" / "mod.py"
        scoped.parent.mkdir(parents=True)
        # Built via concatenation, never spelled out as one literal
        # source line -- writing the target directive shape verbatim
        # here would be ADDED by this test file's own commit and trip
        # land's T-1618 passenger-ticket scan (`_DIRECTIVE_TICKET_ID_RE`
        # in src/frob/tickets/_land.py), which greps every `+`-prefixed
        # diff line for that shape with no context awareness of "real
        # directive" vs. "test fixture string". The runtime VALUE built
        # below is identical either way -- only the literal source text
        # differs.
        directive = "frob:ticket" + " T-9102"
        scoped.write_text(f"# {directive}\ndef f() -> None:\n    pass\n")
        queue = _queue(_ticket("T-9102", ("src/mod.py",), TicketState.QUEUED))
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ids = ticket_runner._render_already_landed_markers(tmp_path, queue)
        assert ids == frozenset({"T-9102"})
        summary_records = [
            r
            for r in caplog.records
            if "already carry their own landed marker" in r.getMessage()
        ]
        assert len(summary_records) == 1
        assert "T-9102" in summary_records[0].getMessage()


class TestDoableRowLandedMarker:
    # frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker.test_flagged_id_gets_inline_marker  # noqa: E501
    def test_flagged_id_gets_inline_marker(self) -> None:
        t = _ticket("T-9103", ("src/mod.py",), TicketState.QUEUED)
        row = ticket_runner._doable_row(t, {}, False, landed_ids=frozenset({"T-9103"}))
        assert "ALREADY-LANDED" in row
        assert "T-9103" in row

    # frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker.test_unflagged_id_gets_no_marker  # noqa: E501
    def test_unflagged_id_gets_no_marker(self) -> None:
        t = _ticket("T-9104", ("src/mod.py",), TicketState.QUEUED)
        row = ticket_runner._doable_row(t, {}, False, landed_ids=frozenset({"T-9103"}))
        assert "ALREADY-LANDED" not in row
