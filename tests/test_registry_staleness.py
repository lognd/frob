"""Tests for frob.registry._staleness -- the T-0560 gate-rule-staleness
auto-file mechanism (missing_gate_rule_ids / sync_gate_rule_entries)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from frob.gates._models import Severity
from frob.gates._registry_exhaustiveness import registry_gate
from frob.registry._corpus import CorpusError
from frob.registry._staleness import missing_gate_rule_ids, sync_gate_rule_entries
from frob.tickets._models import TicketQueue

# frob:ticket T-0560
_FIXTURE = """\
schema_version: 1
gate_rule_total: 1
gate_rule_entries:
  - id: "CHK-GATE-REF001"
    name: "REF001 is a live, enforced gate rule"
    disposition: "handled_by:REF001"
    cross_refs: []
"""


# frob:ticket T-0560
def _write_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "check-coverage.yaml"
    path.write_text(_FIXTURE)
    return path


# frob:ticket T-0560
class TestMissingGateRuleIds:
    # frob:tests \
    # tests/test_registry_staleness.py::TestMissingGateRuleIds.test_finds_rules_with_no\
    # _entry
    # frob:ticket T-0560
    def test_finds_rules_with_no_entry(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)
        missing = missing_gate_rule_ids(path, frozenset({"REF001", "COV001"}))
        assert missing == frozenset({"COV001"})

    # frob:ticket T-0560
    def test_fully_covered_is_empty(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)
        missing = missing_gate_rule_ids(path, frozenset({"REF001"}))
        assert missing == frozenset()

    # frob:ticket T-0560
    def test_unreadable_file_is_empty(self, tmp_path: Path) -> None:
        missing = missing_gate_rule_ids(tmp_path / "nope.yaml", frozenset({"COV001"}))
        assert missing == frozenset()


# frob:ticket T-0560
class TestSyncGateRuleEntries:
    # frob:tests \
    # tests/test_registry_staleness.py::TestSyncGateRuleEntries.test_appends_every_miss\
    # ing_rule
    # frob:ticket T-0560
    def test_appends_every_missing_rule(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)

        result = sync_gate_rule_entries(path, frozenset({"REF001", "COV001", "COV002"}))

        assert result.is_ok
        assert result.danger_ok == ("COV001", "COV002")
        text = path.read_text()
        assert 'id: "CHK-GATE-COV001"' in text
        assert 'disposition: "handled_by:COV001"' in text
        assert 'id: "CHK-GATE-COV002"' in text
        assert "gate_rule_total: 3" in text

    # frob:ticket T-0560
    def test_already_in_sync_returns_empty_tuple(self, tmp_path: Path) -> None:
        path = _write_fixture(tmp_path)

        result = sync_gate_rule_entries(path, frozenset({"REF001"}))

        assert result.is_ok
        assert result.danger_ok == ()
        assert path.read_text() == _FIXTURE

    # frob:ticket T-0560
    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        result = sync_gate_rule_entries(tmp_path / "nope.yaml", frozenset({"COV001"}))
        assert result.is_err
        assert result.danger_err == CorpusError.FileNotFound


# frob:ticket T-0560
class TestReg010Gate:
    # frob:tests \
    # tests/test_registry_staleness.py::TestReg010Gate.test_missing_gate_rule_entry_war\
    # ns
    # frob:ticket T-0560
    def test_missing_gate_rule_entry_warns(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "check-coverage.yaml").write_text(_FIXTURE)

        violations = registry_gate(
            tmp_path,
            TicketQueue(tickets={}),
            frozenset({"REF001", "COV001"}),
            registry_dir,
        )

        rules = [v.rule for v in violations]
        assert "REG010" in rules
        reg010 = next(v for v in violations if v.rule == "REG010")
        assert reg010.severity == Severity.WARN

    # frob:ticket T-0560
    def test_fully_covered_no_reg010(self, tmp_path: Path) -> None:
        registry_dir = tmp_path / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "check-coverage.yaml").write_text(_FIXTURE)

        violations = registry_gate(
            tmp_path,
            TicketQueue(tickets={}),
            frozenset({"REF001"}),
            registry_dir,
        )

        rules = [v.rule for v in violations]
        assert "REG010" not in rules


# frob:ticket T-1359
class TestSyncGateRuleEntriesCrashSafety:
    """T-1359: `sync_gate_rule_entries` writes `check-coverage.yaml` via
    `frob.tickets._store.atomic_write` -- a process killed mid-rename must
    leave the ORIGINAL file intact rather than half-rewritten (the T-1338
    hazard class T-1348 already closed for `frob.gates._fix_engine`)."""

    def test_leaves_original_on_replace_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_registry_staleness.py::TestSyncGateRuleEntriesCrashSafety.test_lea\
        # ves_original_on_replace_failure
        path = _write_fixture(tmp_path)
        original = path.read_text(encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        result = sync_gate_rule_entries(path, frozenset({"REF001", "NEW001"}))

        assert result.is_err
        assert result.danger_err == CorpusError.WriteFailed
        assert path.read_text(encoding="utf-8") == original
        leftovers = [p for p in tmp_path.iterdir() if p.name != "check-coverage.yaml"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"
