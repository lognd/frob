"""frob.stats._agentic: non-gated agentic time/token report (T-0178)."""

from __future__ import annotations

import json
from pathlib import Path

from frob.stats import agentic_report
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
