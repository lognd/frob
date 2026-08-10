"""Tests for `frob.telemetry` (T-1939): per-run rule-level firing counts,
appended to the existing `.frob/telemetry.jsonl` stream."""

from __future__ import annotations

import json
from pathlib import Path

from frob.gates._models import GateReport, GateStats, Severity, Violation
from frob.telemetry import RULE_COUNTS_KIND, record_rule_firing_counts, rule_firing_counts


def _violation(rule: str, file: str = "a.py") -> Violation:
    return Violation(
        rule=rule,
        severity=Severity.WARN,
        file=file,
        line=1,
        message=f"{rule}: test finding",
    )


class TestRuleFiringCounts:
    """`rule_firing_counts`: kept and waived violations both count, a
    rule with zero findings this run is simply absent from the map."""

    # frob:ticket T-1939
    # frob:tests src/frob/telemetry/__init__.py::rule_firing_counts kind="unit"
    def test_counts_kept_violations(self) -> None:
        report = GateReport(
            violations=(_violation("DEAD001"), _violation("DEAD001"), _violation("WIRE001")),
            waived=(),
            stats=GateStats(),
        )
        assert rule_firing_counts(report) == {"DEAD001": 2, "WIRE001": 1}

    # frob:ticket T-1939
    # frob:tests src/frob/telemetry/__init__.py::rule_firing_counts kind="unit"
    def test_waived_violations_still_count_as_fired(self) -> None:
        report = GateReport(
            violations=(),
            waived=(_violation("COV001"),),
            stats=GateStats(),
        )
        assert rule_firing_counts(report) == {"COV001": 1}

    # frob:ticket T-1939
    # frob:tests src/frob/telemetry/__init__.py::rule_firing_counts kind="unit"
    def test_kept_and_waived_of_the_same_rule_combine(self) -> None:
        report = GateReport(
            violations=(_violation("PERF001"),),
            waived=(_violation("PERF001"), _violation("PERF001")),
            stats=GateStats(),
        )
        assert rule_firing_counts(report) == {"PERF001": 3}

    # frob:ticket T-1939
    # frob:tests src/frob/telemetry/__init__.py::rule_firing_counts kind="unit"
    def test_empty_report_produces_an_empty_map(self) -> None:
        report = GateReport(violations=(), waived=(), stats=GateStats())
        assert rule_firing_counts(report) == {}


class TestRecordRuleFiringCounts:
    """`record_rule_firing_counts`: appends exactly one JSONL event via
    the existing `frob.app.telemetry.append_event` mechanism."""

    # frob:ticket T-1939
    def test_appends_one_event_with_every_fired_rule(self, tmp_path: Path) -> None:
        # frob:tests src/frob/telemetry/__init__.py::record_rule_firing_counts \
        # kind="unit"
        report = GateReport(
            violations=(_violation("DEAD001"),),
            waived=(_violation("WIRE001"),),
            stats=GateStats(),
        )
        record_rule_firing_counts(tmp_path, report)
        lines = (tmp_path / ".frob" / "telemetry.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["kind"] == RULE_COUNTS_KIND
        assert record["rule_counts"] == {"DEAD001": 1, "WIRE001": 1}
        assert record["distinct_rules_fired"] == 2
        assert "iso_ts" in record

    # frob:ticket T-1939
    def test_empty_report_appends_a_zero_rule_event(self, tmp_path: Path) -> None:
        # frob:tests src/frob/telemetry/__init__.py::record_rule_firing_counts \
        # kind="unit"
        report = GateReport(violations=(), waived=(), stats=GateStats())
        record_rule_firing_counts(tmp_path, report)
        lines = (tmp_path / ".frob" / "telemetry.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["rule_counts"] == {}
        assert record["distinct_rules_fired"] == 0

    # frob:ticket T-1939
    def test_respects_no_telemetry_opt_out(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/telemetry/__init__.py::record_rule_firing_counts \
        # kind="unit"
        monkeypatch.setenv("FROB_NO_TELEMETRY", "1")
        report = GateReport(
            violations=(_violation("DEAD001"),), waived=(), stats=GateStats()
        )
        record_rule_firing_counts(tmp_path, report)
        assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()
