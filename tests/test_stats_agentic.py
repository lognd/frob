"""frob.stats._agentic: non-gated agentic time/token report (T-0178)."""

from __future__ import annotations

import json
from pathlib import Path

from frob.stats import agentic_report, dispatch_cost_report
from frob.stats._agentic import TELEMETRY_REL


def _write(root: Path, records: list[dict]) -> None:
    path = root / TELEMETRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record))
            fh.write("\n")


def test_empty_stream_yields_zeroed_report(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    report = agentic_report(tmp_path)
    assert report.event_count == 0
    assert report.category_time == ()
    assert report.top_time_sinks == ()
    assert report.retread_candidates == ()
    assert report.ticket_cycle_times == ()
    assert report.tool_tokens == ()


def test_category_time_buckets_by_subcommand(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    _write(
        tmp_path,
        [
            {"kind": "cli", "subcommand": "check", "args_head": "", "duration_ms": 100},
            {"kind": "cli", "subcommand": "check", "args_head": "", "duration_ms": 50},
            {"kind": "cli", "subcommand": "test", "args_head": "", "duration_ms": 200},
            {"kind": "cli", "subcommand": "outline", "args_head": "", "duration_ms": 5},
        ],
    )
    report = agentic_report(tmp_path)
    by_cat = {c.category: c for c in report.category_time}
    assert by_cat["frob-check"].total_ms == 150
    assert by_cat["frob-check"].count == 2
    assert by_cat["test-suite"].total_ms == 200
    assert by_cat["other"].total_ms == 5


def test_top_time_sinks_orders_descending(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    _write(
        tmp_path,
        [
            {"kind": "cli", "subcommand": "a", "args_head": "", "duration_ms": 1},
            {"kind": "cli", "subcommand": "b", "args_head": "", "duration_ms": 99},
        ],
    )
    report = agentic_report(tmp_path, top_n=1)
    assert len(report.top_time_sinks) == 1
    assert report.top_time_sinks[0].subcommand == "b"


def test_retread_candidates_require_repeat_and_known_tree_hash(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    _write(
        tmp_path,
        [
            {
                "kind": "cli",
                "subcommand": "check",
                "args_head": "",
                "duration_ms": 10,
                "tree_hash": "abc123",
            },
            {
                "kind": "cli",
                "subcommand": "check",
                "args_head": "",
                "duration_ms": 12,
                "tree_hash": "abc123",
            },
            {
                "kind": "cli",
                "subcommand": "check",
                "args_head": "",
                "duration_ms": 5,
                "tree_hash": "unknown",
            },
        ],
    )
    report = agentic_report(tmp_path)
    assert len(report.retread_candidates) == 1
    candidate = report.retread_candidates[0]
    assert candidate.run_count == 2
    assert candidate.tree_hash == "abc123"
    assert candidate.total_ms == 22


def test_ticket_cycle_time_from_transition_events(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    _write(
        tmp_path,
        [
            {
                "kind": "ticket",
                "ticket_id": "T-0001",
                "event": "created",
                "iso_ts": "2026-01-01T00:00:00.000Z",
            },
            {
                "kind": "ticket",
                "ticket_id": "T-0001",
                "event": "started",
                "iso_ts": "2026-01-01T01:00:00.000Z",
            },
            {
                "kind": "ticket",
                "ticket_id": "T-0001",
                "event": "done",
                "iso_ts": "2026-01-01T02:00:00.000Z",
            },
        ],
    )
    report = agentic_report(tmp_path)
    assert len(report.ticket_cycle_times) == 1
    ct = report.ticket_cycle_times[0]
    assert ct.ticket_id == "T-0001"
    assert ct.lead_time_s == 7200.0
    assert ct.cycle_time_s == 3600.0


def test_tool_tokens_sums_output_tokens_per_tool(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    _write(
        tmp_path,
        [
            {"kind": "tool", "tool": "Bash", "output_tokens_est": 100},
            {"kind": "tool", "tool": "Bash", "output_tokens_est": 50},
            {"kind": "tool", "tool": "Read", "output_tokens_est": 10},
        ],
    )
    report = agentic_report(tmp_path)
    by_tool = {t.tool: t for t in report.tool_tokens}
    assert by_tool["Bash"].total_tokens == 150
    assert by_tool["Bash"].call_count == 2
    assert by_tool["Read"].total_tokens == 10


def test_malformed_lines_are_skipped_not_raised(tmp_path: Path):
    # frob:tests src/frob/stats/_agentic.py::agentic_report
    path = tmp_path / TELEMETRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"kind": "cli", "subcommand": "check", "duration_ms": 1}\nnot json\n'
    )
    report = agentic_report(tmp_path)
    assert report.event_count == 1


class TestDispatchCostReport:
    """T-1724: joining `kind="dispatch"` boundary events against
    `kind="tool"` cost and `kind="ticket"` delivery events in the same
    telemetry stream."""

    def test_empty_stream_yields_empty_report(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        report = dispatch_cost_report(tmp_path)
        assert report.dispatches == ()
        assert report.tokens_per_landed_ticket is None
        assert report.zero_delivery_dispatch_ids == ()
        assert report.cold_start_floor_tokens is None
        assert report.marginal_run_deltas == ()

    def test_dispatch_with_no_tool_events_has_unmeasured_not_zero_tokens(
        self, tmp_path: Path
    ):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                    "cold_start": True,
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        assert len(report.dispatches) == 1
        d = report.dispatches[0]
        assert d.output_tokens_delta is None, "unmeasured must never render as 0"
        assert d.tool_call_count == 0
        assert d.wall_clock_s == 300.0
        assert d.cold_start is True

    def test_tool_events_join_by_window_and_sum_tokens(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                },
                {
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 100,
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "tool",
                    "tool": "Read",
                    "output_tokens_est": 40,
                    "iso_ts": "2026-08-07T10:03:00Z",
                },
                {
                    # outside the window -- must NOT be attributed to d1.
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 999,
                    "iso_ts": "2026-08-07T11:00:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        d = report.dispatches[0]
        assert d.output_tokens_delta == 140
        assert d.tool_call_count == 2

    def test_delivered_tickets_join_by_window(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                },
                {
                    "kind": "ticket",
                    "ticket_id": "T-0001",
                    "event": "done",
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "ticket",
                    "ticket_id": "T-0002",
                    "event": "started",  # not done/dropped -- excluded
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "ticket",
                    "ticket_id": "T-0003",
                    "event": "done",
                    "iso_ts": "2026-08-07T12:00:00Z",  # outside window
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        assert report.dispatches[0].tickets_delivered == ("T-0001",)

    def test_zero_delivery_dispatch_flagged_only_when_measurably_costly(
        self, tmp_path: Path
    ):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "wasted",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                },
                {
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 500,
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "wasted",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
                {
                    # zero delivery AND no measured tool cost -- must NOT
                    # be flagged as "consumed budget".
                    "kind": "dispatch",
                    "dispatch_id": "unmeasured",
                    "event": "start",
                    "iso_ts": "2026-08-07T11:00:00Z",
                    "worktree": "wt2",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "unmeasured",
                    "event": "end",
                    "iso_ts": "2026-08-07T11:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        assert report.zero_delivery_dispatch_ids == ("wasted",)
        assert report.cold_start_floor_tokens == 500.0

    def test_tokens_per_landed_ticket(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                },
                {
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 200,
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "ticket",
                    "ticket_id": "T-0001",
                    "event": "done",
                    "iso_ts": "2026-08-07T10:03:00Z",
                },
                {
                    "kind": "ticket",
                    "ticket_id": "T-0002",
                    "event": "dropped",
                    "iso_ts": "2026-08-07T10:03:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "d1",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        # 200 tokens / 2 delivered tickets
        assert report.tokens_per_landed_ticket == 100.0

    def test_marginal_run_deltas_ordered_and_computed_per_worktree(
        self, tmp_path: Path
    ):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "run1",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                    "worktree": "wt1",
                    "cold_start": True,
                },
                {
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 100,
                    "iso_ts": "2026-08-07T10:02:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "run1",
                    "event": "end",
                    "iso_ts": "2026-08-07T10:05:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "run2",
                    "event": "start",
                    "iso_ts": "2026-08-07T11:00:00Z",
                    "worktree": "wt1",
                    "cold_start": False,
                },
                {
                    "kind": "tool",
                    "tool": "Bash",
                    "output_tokens_est": 350,
                    "iso_ts": "2026-08-07T11:02:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "run2",
                    "event": "end",
                    "iso_ts": "2026-08-07T11:05:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        deltas = report.marginal_run_deltas
        assert len(deltas) == 2
        assert deltas[0].run_index == 1
        assert deltas[0].dispatch_id == "run1"
        assert deltas[0].marginal_tokens_delta is None
        assert deltas[1].run_index == 2
        assert deltas[1].dispatch_id == "run2"
        assert deltas[1].marginal_tokens_delta == 250

    def test_dispatches_ordered_by_start_ts_missing_last(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        _write(
            tmp_path,
            [
                {
                    "kind": "dispatch",
                    "dispatch_id": "second",
                    "event": "start",
                    "iso_ts": "2026-08-07T11:00:00Z",
                },
                {
                    "kind": "dispatch",
                    "dispatch_id": "first",
                    "event": "start",
                    "iso_ts": "2026-08-07T10:00:00Z",
                },
                {
                    # no "start" event at all -- unparseable/missing
                    # start_ts, must sort last.
                    "kind": "dispatch",
                    "dispatch_id": "no-start",
                    "event": "end",
                    "iso_ts": "2026-08-07T12:00:00Z",
                },
            ],
        )
        report = dispatch_cost_report(tmp_path)
        ids = [d.dispatch_id for d in report.dispatches]
        assert ids == ["first", "second", "no-start"]

    def test_malformed_lines_skipped_not_raised(self, tmp_path: Path):
        # frob:tests src/frob/stats/_agentic.py::dispatch_cost_report
        path = tmp_path / TELEMETRY_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"kind": "dispatch", "dispatch_id": "d1"}\nnot json\n')
        report = dispatch_cost_report(tmp_path)
        # missing "event" field -- skipped by _group_dispatch_marks, not raised.
        assert report.dispatches == ()
