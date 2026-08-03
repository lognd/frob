"""T-1400 continuation: genuine TEST005 branch gaps in `frob.app.perf_runner`
identified across this ticket's prior sessions' scoped-coverage sampling
(perf_runner.py 88% -> higher: 137-139, 157-159, 331-332, 349, 518, 525-531,
657-671). Each test below asserts real rendered/behavioral output, not just
that a call does not raise -- matching this repo's evidence discipline
(docs/guides/agent-playbook.md section 5).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from frob.app.config import AppConfig
from frob.app.perf_runner import (
    _annotate_gutters,
    _collect_stacks,
    _collect_stacks_from_file,
    _persist_run,
    _print_findings,
    _print_heat_table,
    _smell_rules_by_ref,
)
from frob.app.perf_runner import (
    run as perf_run,
)
from frob.gates._models import Severity, Violation
from frob.perf._hotgraph import HitStream, SectionHit
from frob.perf._models import HeatEntry
from frob.perf._sketch_store import _close_all


# frob:waive DEAD001 reason="pytest autouse fixture -- teardown-only, never referenced by name/call token anywhere; matches tests/unit/perf/test_persist_run_cli.py's identical waiver for the same fixture shape"  # noqa: E501
@pytest.fixture(autouse=True)
def _teardown_sketch_store():
    yield
    _close_all()


def _record(path: str, start_line: int, symref: str) -> SimpleNamespace:
    """A minimal stand-in for a graph snapshot's per-symbol record: only
    the two attribute paths `_smell_rules_by_ref`/`_annotate_gutters`
    actually read (`record.id.path`, `record.span[0]`, plus the symref
    key itself the caller indexes by)."""
    return SimpleNamespace(
        id=SimpleNamespace(path=path), span=(start_line, start_line + 3), symref=symref
    )


class TestSmellRulesByRef:
    """perf_runner.py 137-139: the violation-to-symref join loop."""

    def test_matching_violation_is_attributed_to_its_symbol(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef.test_matching_violation_is_attributed_to_its_symbol  # noqa: E501
        record = _record("mod.py", 10, "mod.py::hot_fn")
        snapshot = SimpleNamespace(symbols={"mod.py::hot_fn": record})
        violation = Violation(
            rule="PERF001",
            severity=Severity.WARN,
            file="mod.py",
            line=10,
            message="smells hot",
        )
        by_ref = _smell_rules_by_ref([violation], snapshot)
        assert by_ref == {"mod.py::hot_fn": ("PERF001",)}

    def test_violation_with_no_matching_symbol_is_dropped(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef.test_violation_with_no_matching_symbol_is_dropped  # noqa: E501
        record = _record("mod.py", 10, "mod.py::hot_fn")
        snapshot = SimpleNamespace(symbols={"mod.py::hot_fn": record})
        violation = Violation(
            rule="PERF001",
            severity=Severity.WARN,
            file="mod.py",
            line=999,  # no symbol starts here
            message="unmatched",
        )
        by_ref = _smell_rules_by_ref([violation], snapshot)
        assert by_ref == {}

    def test_two_violations_on_the_same_symbol_accumulate_both_rules(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestSmellRulesByRef.test_two_violations_on_the_same_symbol_accumulate_both_rules  # noqa: E501
        record = _record("mod.py", 10, "mod.py::hot_fn")
        snapshot = SimpleNamespace(symbols={"mod.py::hot_fn": record})
        violations = [
            Violation(
                rule="PERF001",
                severity=Severity.WARN,
                file="mod.py",
                line=10,
                message="a",
            ),
            Violation(
                rule="PERF002",
                severity=Severity.WARN,
                file="mod.py",
                line=10,
                message="b",
            ),
        ]
        by_ref = _smell_rules_by_ref(violations, snapshot)
        assert by_ref == {"mod.py::hot_fn": ("PERF001", "PERF002")}


class TestPrintHeatTable:
    """perf_runner.py 157-159: the per-entry heat-row rendering loop."""

    def test_renders_one_row_per_entry_with_smell_tag(self, capsys) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable.test_renders_one_row_per_entry_with_smell_tag  # noqa: E501
        entries = [
            HeatEntry(
                ref="mod.py::hot_fn",
                cum_s=1.5,
                self_s=0.5,
                ncalls=3,
                smells=("PERF001",),
            ),
            HeatEntry(ref="mod.py::cold_fn", cum_s=0.1, self_s=0.1, ncalls=1),
        ]
        _print_heat_table(entries, unattributed_s=0.25)
        out = capsys.readouterr().out
        assert "mod.py::hot_fn" in out
        assert "[PERF001]" in out
        assert "mod.py::cold_fn" in out
        assert "unattributed: 0.250s" in out

    def test_empty_entries_still_prints_header_and_unattributed(self, capsys) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestPrintHeatTable.test_empty_entries_still_prints_header_and_unattributed  # noqa: E501
        _print_heat_table([], unattributed_s=0.0)
        out = capsys.readouterr().out
        assert "unattributed: 0.000s" in out


class TestCollectStacksFromFileRequiresFile:
    """perf_runner.py 331-332: `--file`/`--sampler` are mutually exclusive
    inputs to `_collect_stacks`; neither being set must exit 1, not crash
    with an AttributeError on a None `perf_file`."""

    def test_missing_file_exits_1_with_logged_error(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestCollectStacksFromFileRequiresFile.test_missing_file_exits_1_with_logged_error  # noqa: E501
        cfg = AppConfig(perf_command="collect", perf_path=tmp_path, perf_file=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            _collect_stacks_from_file(cfg)
        assert exc.value.code == 1
        assert "requires --file" in caplog.text


class TestCollectStacksSamplerBranch:
    """perf_runner.py 349: `--sampler` routes to the live-sampler path
    instead of `_collect_stacks_from_file`."""

    def test_sampler_flag_dispatches_to_sampler_collector(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestCollectStacksSamplerBranch.test_sampler_flag_dispatches_to_sampler_collector  # noqa: E501
        cfg = AppConfig(perf_command="collect", perf_path=tmp_path, perf_sampler=True)
        sentinel = ["sampled-stack"]
        with patch(
            "frob.app.perf_runner._collect_stacks_via_sampler", return_value=sentinel
        ) as mocked:
            result = _collect_stacks(cfg)
        mocked.assert_called_once_with(cfg)
        assert result is sentinel


class TestPrintFindingsAdvisoryLoop:
    """perf_runner.py 518: the per-advisory rendering loop (findings render
    on a separate, already-covered path; advisories previously never hit
    a populated non-empty list)."""

    def test_renders_one_line_per_advisory(self, capsys) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestPrintFindingsAdvisoryLoop.test_renders_one_line_per_advisory  # noqa: E501
        advisories = [
            Violation(
                rule="PERF010",
                severity=Severity.WARN,
                file="a.py",
                line=1,
                message="fan-in",
            ),
            Violation(
                rule="PERF011",
                severity=Severity.WARN,
                file="b.py",
                line=2,
                message="heavy tail",
            ),
        ]
        _print_findings([], advisories)
        out = capsys.readouterr().out
        assert "PERF010: fan-in" in out
        assert "PERF011: heavy tail" in out


class TestAnnotateGuttersLoop:
    """perf_runner.py 525-531: `_annotate_gutters`'s per-entry filter/join
    loop -- entries for a different file are skipped, entries with no
    matching symbol record are skipped, and a genuine match produces a
    gutter keyed by the symbol's start line."""

    def test_entry_for_a_different_file_is_skipped(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop.test_entry_for_a_different_file_is_skipped  # noqa: E501
        report = SimpleNamespace(
            entries=[HeatEntry(ref="other.py::fn", cum_s=1.0, self_s=1.0, ncalls=1)]
        )
        snapshot = SimpleNamespace(symbols={})
        gutters = _annotate_gutters("mod.py", report, snapshot)
        assert gutters == {}

    def test_entry_with_no_symbol_record_is_skipped(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop.test_entry_with_no_symbol_record_is_skipped  # noqa: E501
        report = SimpleNamespace(
            entries=[
                HeatEntry(ref="mod.py::missing_fn", cum_s=1.0, self_s=1.0, ncalls=1)
            ]
        )
        snapshot = SimpleNamespace(symbols={})
        gutters = _annotate_gutters("mod.py", report, snapshot)
        assert gutters == {}

    def test_matching_entry_produces_a_gutter_at_the_symbols_start_line(self) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestAnnotateGuttersLoop.test_matching_entry_produces_a_gutter_at_the_symbols_start_line  # noqa: E501
        record = _record("mod.py", 42, "mod.py::hot_fn")
        report = SimpleNamespace(
            entries=[HeatEntry(ref="mod.py::hot_fn", cum_s=2.5, self_s=1.0, ncalls=4)]
        )
        snapshot = SimpleNamespace(symbols={"mod.py::hot_fn": record})
        gutters = _annotate_gutters("mod.py", report, snapshot)
        assert gutters == {42: "2.500s/4x"}


def _perf_script(blocks: list[tuple[float, str]]) -> str:
    """A `perf script`-format profile from `(weight, frame_loc)` pairs --
    same construction `tests/unit/perf/test_persist_run_cli.py` uses."""
    parts = []
    for weight, loc in blocks:
        parts.append(f"myprog  1 1 {weight}: 1 cycles:\n\t401234 fn+0x10 ({loc})\n")
    return "\n".join(parts)


def _write_workload(tmp_path: Path) -> tuple[Path, int]:
    """A tiny python module with one function -- returns (path, line) of a
    resolvable line inside the function body."""
    text = "def hot_loop():\n    total = 0\n    total += 1\n    return total\n"
    path = tmp_path / "workload.py"
    path.write_text(text)
    return path, 2


class TestPersistRunUnresolvedSection:
    """perf_runner.py 470: `_persist_run`'s `if section is None: continue`
    -- a hit's `section_id` present in `run_weight` but absent from the
    section index (a stale/dangling id) must be skipped, not raise a
    KeyError or persist a bogus sketch."""

    def test_hit_with_unknown_section_id_is_skipped_without_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestPersistRunUnresolvedSection.test_hit_with_unknown_section_id_is_skipped_without_error  # noqa: E501
        cfg = AppConfig(perf_command="collect", perf_path=tmp_path)
        stream = HitStream(
            section_hits=(SectionHit(section_id="ghost-section", weight=1.0),)
        )
        findings, advisories = _persist_run(cfg, {}, stream)
        # The dangling id never resolves to a real Section, so nothing is
        # persisted and no finding/advisory is produced for it.
        assert findings == []
        assert advisories == []


class TestHotDefaultTableRendering:
    """perf_runner.py 657-671: `frob perf hot`'s DEFAULT (non-`--json`)
    table path -- `_hot_json` already had coverage (T-1276-era tests);
    this plain-table branch never had a dedicated exerciser."""

    def test_hot_without_json_renders_a_table_with_header_and_row(
        self, tmp_path: Path, capsys
    ) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering.test_hot_without_json_renders_a_table_with_header_and_row  # noqa: E501
        workload, line = _write_workload(tmp_path)
        profile = tmp_path / "p.script"
        profile.write_text(_perf_script([(1.0, f"{workload}:{line}")]))

        perf_run(
            AppConfig(perf_command="collect", perf_path=tmp_path, perf_file=profile)
        )
        capsys.readouterr()

        perf_run(AppConfig(perf_command="hot", perf_path=tmp_path))
        out = capsys.readouterr().out
        assert "label" in out and "p50" in out and "p90" in out
        assert "hot_loop" in out

    def test_hot_top_truncates_the_table_rows(self, tmp_path: Path, capsys) -> None:
        # frob:tests tests/unit/test_perf_runner_t1400.py::TestHotDefaultTableRendering.test_hot_top_truncates_the_table_rows  # noqa: E501
        workload, line = _write_workload(tmp_path)
        profile = tmp_path / "p.script"
        profile.write_text(_perf_script([(1.0, f"{workload}:{line}")]))

        perf_run(
            AppConfig(perf_command="collect", perf_path=tmp_path, perf_file=profile)
        )
        capsys.readouterr()

        perf_run(AppConfig(perf_command="hot", perf_path=tmp_path, perf_top=0))
        out = capsys.readouterr().out
        # Header still prints; --top 0 slices every data row away.
        assert "hot_loop" not in out
