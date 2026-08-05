"""T-1528: `frob ticket list`'s always-on state-summary footer and the
opt-in `--stats` velocity/ETA line -- unit tests over the `_query` render
helpers plus one end-to-end `_list` caplog pass on a real tiny ledger."""

# frob:ticket T-1528
# frob:waive OPAQUE001 reason="monkeypatch with a literal dotted-path string target \
# (frob.tickets.ticket_flow), the standard test seam this suite uses; restored by \
# teardown"

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._query import _list, _stats_line, _summary_footer
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
)
from frob.tickets._models import TicketFlowReport, TicketFlowRow
from frob.tickets._store import atomic_write, ledger_path


# frob:ticket T-1528
def _test_seed(root: Path, n: int = 2) -> None:
    atomic_write(ledger_path(root), "# Tickets\n\n")
    for i in range(n):
        created = new_ticket(
            root,
            TicketSpec(
                title=f"ticket {i}", kind=TicketKind.FEATURE, origin=Origin.AGENT
            ),
        )
        assert created.is_ok


# frob:ticket T-1528
class TestSummaryFooter:
    # frob:ticket T-1528
    def test_counts_per_state(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestSummaryFooter.test_counts_per_sta\
        # te
        _test_seed(tmp_path, n=3)
        queue = load_active(tmp_path).danger_ok
        line = _summary_footer(tmp_path, queue)
        assert line == "summary: 3 active (3 queued)"

    # frob:ticket T-1528
    def test_empty_queue(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestSummaryFooter.test_empty_queue
        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")
        queue = load_active(tmp_path).danger_ok
        assert _summary_footer(tmp_path, queue) == "summary: 0 active (empty)"

    # frob:ticket T-1530
    def test_leased_queued_ticket_counts_as_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestSummaryFooter.test_leased_queued_\
        # ticket_counts_as_in_progress
        """T-1530: the census must match the rows -- a ledger-queued ticket
        with a live worktree lease renders [in-progress@...] in the rows,
        so it counts as in-progress here, not queued."""
        _test_seed(tmp_path, n=2)
        queue = load_active(tmp_path).danger_ok
        leased_id = sorted(queue.tickets)[0]

        class _FakeLease:
            ticket_id = leased_id
            worktree = str(tmp_path / "wt")

        monkeypatch.setattr("frob.tickets.read_all_leases", lambda root: [_FakeLease()])
        line = _summary_footer(tmp_path, queue)
        assert line == "summary: 2 active (1 queued, 1 in-progress)"


# frob:ticket T-1528
class TestStatsLine:
    # frob:ticket T-1528
    def test_renders_rates_cycle_and_eta(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestStatsLine.test_renders_rates_cycl\
        # e_and_eta
        _test_seed(tmp_path)
        queue = load_active(tmp_path).danger_ok
        fake = TicketFlowReport(
            rows=(
                TicketFlowRow(day=date(2026, 8, 2), filed=2, landed=6),
                TicketFlowRow(day=date(2026, 8, 3), filed=1, landed=5),
                TicketFlowRow(day=date(2026, 8, 4), filed=0, landed=4),
            ),
            open_count=30,
            trailing_net_rate=-4.0,
            median_cycle_days=2.5,
        )
        monkeypatch.setattr("frob.tickets.ticket_flow", lambda root, q, **kw: fake)
        line = _stats_line(tmp_path, queue)
        assert "open 30" in line
        assert "filed 1.0/d" in line
        assert "landed 5.0/d" in line
        assert "net -4.0/d" in line
        assert "median cycle 2.5d" in line
        assert "ETA ~8d" in line

    # frob:ticket T-1528
    def test_labels_unshrinking_and_missing_cycle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestStatsLine.test_labels_unshrinking\
        # _and_missing_cycle
        _test_seed(tmp_path)
        queue = load_active(tmp_path).danger_ok
        fake = TicketFlowReport(
            rows=(TicketFlowRow(day=date(2026, 8, 4), filed=1, landed=0),),
            open_count=5,
            trailing_net_rate=1.0,
            median_cycle_days=None,
        )
        monkeypatch.setattr("frob.tickets.ticket_flow", lambda root, q, **kw: fake)
        line = _stats_line(tmp_path, queue)
        assert "median cycle n/a" in line
        assert "ETA not shrinking" in line


# frob:ticket T-1528
class TestListFooterEndToEnd:
    # frob:ticket T-1528
    def test_list_always_prints_summary(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests \
        # tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd.test_list_alwa\
        # ys_prints_summary
        _test_seed(tmp_path, n=2)
        cfg = AppConfig(ticket_command="list")
        with caplog.at_level("INFO"):
            _list(tmp_path, cfg)
        assert any(r.message.startswith("summary: 2 active") for r in caplog.records)
