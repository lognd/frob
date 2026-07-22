"""Tests for `frob.gates._ratchet` (T-0569): ratchet-pool baseline
snapshot/clear + severity resolution (docs/modules/gates.md#ratchet-pools).

Non-vacuous fixture proving the ticket's own acceptance: a baselined
finding stays warn, a fresh finding errors, and clearing a baseline entry
requires a disposition reason."""

from __future__ import annotations

from pathlib import Path

from frob.gates._ratchet import (
    RatchetError,
    clear_ratchet_entry,
    load_ratchet_lock,
    ratchet_enabled_rules,
    resolve_ratchet_severity,
    snapshot_ratchet,
)


# frob:ticket T-0569
class TestSnapshotRatchet:
    def test_first_snapshot_baselines_every_key(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestSnapshotRatchet.test_first_snapshot_baselines_every_key  # noqa: E501
        result = snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1", "b.py:2"])
        assert result.is_ok, result.err
        pool = result.danger_ok
        assert pool.keys == {"a.py:1", "b.py:2"}

    # frob:ticket T-0569
    def test_second_snapshot_preserves_original_baseline_date(
        self, tmp_path: Path
    ) -> None:
        first = snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"]).danger_ok
        original_date = next(e.baselined for e in first.entries if e.key == "a.py:1")
        second = snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1", "c.py:3"]).danger_ok
        replayed_date = next(e.baselined for e in second.entries if e.key == "a.py:1")
        assert replayed_date == original_date
        assert second.keys == {"a.py:1", "c.py:3"}

    # frob:ticket T-0569
    def test_writes_committed_lock_file(self, tmp_path: Path) -> None:
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        assert (tmp_path / "frob-ratchet.lock.json").is_file()

    # frob:ticket T-0569
    def test_two_rules_do_not_clobber_each_other(self, tmp_path: Path) -> None:
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        snapshot_ratchet(tmp_path, "PII010", ["b.py:2"])
        lock = load_ratchet_lock(tmp_path)
        dead_pool = lock.pool_for("DEAD001")
        pii_pool = lock.pool_for("PII010")
        assert dead_pool is not None and dead_pool.keys == {"a.py:1"}
        assert pii_pool is not None and pii_pool.keys == {"b.py:2"}


# frob:ticket T-0569
class TestResolveRatchetSeverity:
    def test_baselined_finding_stays_warn(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestResolveRatchetSeverity.test_baselined_finding_stays_warn  # noqa: E501
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        lock = load_ratchet_lock(tmp_path)
        assert resolve_ratchet_severity("DEAD001", "a.py:1", lock) == "warn"

    # frob:ticket T-0569
    def test_fresh_finding_errors(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestResolveRatchetSeverity.test_fresh_finding_errors  # noqa: E501
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        lock = load_ratchet_lock(tmp_path)
        assert resolve_ratchet_severity("DEAD001", "z.py:99", lock) == "error"

    # frob:ticket T-0569
    def test_unratcheted_rule_with_no_pool_is_error(self, tmp_path: Path) -> None:
        lock = load_ratchet_lock(tmp_path)
        assert resolve_ratchet_severity("NEVERSEEN001", "x.py:1", lock) == "error"


# frob:ticket T-0569
class TestClearRatchetEntry:
    def test_clearing_requires_a_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestClearRatchetEntry.test_clearing_requires_a_reason  # noqa: E501
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        result = clear_ratchet_entry(tmp_path, "DEAD001", "a.py:1", "   ")
        assert result.is_err
        assert result.danger_err is RatchetError.ClearReasonMissing

    # frob:ticket T-0569
    def test_clearing_with_reason_removes_entry_and_it_now_errors(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestClearRatchetEntry.test_clearing_with_reason_removes_entry_and_it_now_errors  # noqa: E501
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        result = clear_ratchet_entry(tmp_path, "DEAD001", "a.py:1", "fixed the finding")
        assert result.is_ok, result.err
        assert "a.py:1" not in result.danger_ok.keys

        lock = load_ratchet_lock(tmp_path)
        assert resolve_ratchet_severity("DEAD001", "a.py:1", lock) == "error"

    # frob:ticket T-0569
    def test_clearing_unknown_key_is_err(self, tmp_path: Path) -> None:
        snapshot_ratchet(tmp_path, "DEAD001", ["a.py:1"])
        result = clear_ratchet_entry(tmp_path, "DEAD001", "z.py:99", "reason")
        assert result.is_err
        assert result.danger_err is RatchetError.EntryNotFound


# frob:ticket T-0569
class TestRatchetEnabledRules:
    def test_missing_toml_is_empty(self, tmp_path: Path) -> None:
        assert ratchet_enabled_rules(tmp_path) == frozenset()

    # frob:ticket T-0569
    def test_reads_configured_rules(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            '[gates.ratchet]\nrules = ["DEAD001", "PII010"]\n', encoding="utf-8"
        )
        assert ratchet_enabled_rules(tmp_path) == {"DEAD001", "PII010"}

    # frob:ticket T-0569
    def test_missing_table_is_empty(self, tmp_path: Path) -> None:
        (tmp_path / "frob.toml").write_text(
            "[arch]\nmax_file_lines = 800\n", encoding="utf-8"
        )
        assert ratchet_enabled_rules(tmp_path) == frozenset()
