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


# frob:ticket T-1657
class TestLoadRatchetLockErrorPaths:
    def test_malformed_json_treated_as_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths.test_malformed_json_treated_as_empty  # noqa: E501
        """A `frob-ratchet.lock.json` on disk that is not valid JSON must
        make `load_ratchet_lock` return an empty `RatchetLock` (T-0569's
        "no baseline is a valid starting state" contract), never raise."""
        (tmp_path / "frob-ratchet.lock.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        lock = load_ratchet_lock(tmp_path)
        assert lock.pool_for("DEAD001") is None

    def test_schema_mismatch_treated_as_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestLoadRatchetLockErrorPaths.test_schema_mismatch_treated_as_empty  # noqa: E501
        """Valid JSON that fails `RatchetLock`'s schema (a pydantic
        `ValidationError`, a `ValueError` subclass) hits the same
        swallow-and-return-empty branch as malformed JSON."""
        import json

        (tmp_path / "frob-ratchet.lock.json").write_text(
            json.dumps({"pools": "not-a-list"}), encoding="utf-8"
        )
        lock = load_ratchet_lock(tmp_path)
        assert lock.pool_for("DEAD001") is None


# frob:ticket T-1657
class TestRatchetEnabledRulesErrorPaths:
    def test_malformed_toml_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths.test_malformed_toml_returns_empty  # noqa: E501
        """A `frob.toml` that fails to PARSE (`tomllib.TOMLDecodeError`)
        must make `ratchet_enabled_rules` return an empty frozenset, per
        the missing-is-default contract -- never raise."""
        from frob.gates._ratchet import ratchet_enabled_rules

        (tmp_path / "frob.toml").write_text("not = [valid toml", encoding="utf-8")
        assert ratchet_enabled_rules(tmp_path) == frozenset()

    def test_non_list_rules_shape_returns_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestRatchetEnabledRulesErrorPaths.test_non_list_rules_shape_returns_empty  # noqa: E501
        """Valid TOML whose `[gates.ratchet] rules` is not iterable the
        expected way (a bare table, not a list of strings) must still
        return empty rather than raise -- the broad `except Exception`
        missing-is-default branch, distinct from the OSError/TOMLDecodeError
        one."""
        from frob.gates._ratchet import ratchet_enabled_rules

        (tmp_path / "frob.toml").write_text(
            "[gates.ratchet]\nrules = 5\n", encoding="utf-8"
        )
        assert ratchet_enabled_rules(tmp_path) == frozenset()


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


# T-1620: `_mass_invalidation_rules` (`frob.gates._fix_engine_sync`) is the
# other half of this repo's degraded-run defenses, alongside the ratchet
# severity/baseline machinery already tested above -- placed here per this
# ticket's own declared test-file scope rather than a new file, since
# `frob.gates._fix_engine_sync`/`frob.gates.__init__` are both already in
# `src/frob/gates/**` scope but `tests/test_gates.py` (where the ratchet-
# adjacent T-1578 marker tests already live) is not.
# frob:ticket T-1620
class TestMassInvalidationRulesProportional:
    """T-1620: the absolute `_WAIVE004_MASS_INVALIDATION_THRESHOLD` (5) is
    structurally blind to any rule with fewer than 5 live waivers -- a
    rule with exactly 2 live waivers can never reach the threshold no
    matter how degraded the run is. `_mass_invalidation_rules` now also
    flags the PROPORTIONAL case (every one of a rule's live waivers going
    stale in the same run), independent of the absolute count."""

    def test_below_threshold_but_all_live_waivers_stale_is_flagged(self) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional.test_below_threshold_but_all_live_waivers_stale_is_flagged  # noqa: E501
        from frob.gates._fix_engine_sync import _mass_invalidation_rules

        candidates = [("a.py", 1, "DEPR005"), ("b.py", 2, "DEPR005")]
        live_counts = {"DEPR005": 2}

        result = _mass_invalidation_rules(candidates, live_counts)

        assert result == {"DEPR005": 2}

    def test_below_threshold_with_more_live_waivers_than_stale_is_not_flagged(
        self,
    ) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional.test_below_threshold_with_more_live_waivers_than_stale_is_not_flagged  # noqa: E501
        from frob.gates._fix_engine_sync import _mass_invalidation_rules

        candidates = [("a.py", 1, "DEPR005")]
        live_counts = {"DEPR005": 3}

        result = _mass_invalidation_rules(candidates, live_counts)

        assert result == {}

    def test_absolute_threshold_still_fires_with_no_live_count_data(self) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional.test_absolute_threshold_still_fires_with_no_live_count_data  # noqa: E501
        from frob.gates._fix_engine_sync import (
            _WAIVE004_MASS_INVALIDATION_THRESHOLD,
            _mass_invalidation_rules,
        )

        candidates = [
            ("f.py", i, "PERF004") for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD)
        ]

        result = _mass_invalidation_rules(candidates, {})

        assert result == {"PERF004": _WAIVE004_MASS_INVALIDATION_THRESHOLD}

    def test_partial_stale_below_threshold_and_below_live_count_is_not_flagged(
        self,
    ) -> None:
        # frob:tests tests/test_gates_ratchet.py::TestMassInvalidationRulesProportional.test_partial_stale_below_threshold_and_below_live_count_is_not_flagged  # noqa: E501
        from frob.gates._fix_engine_sync import _mass_invalidation_rules

        candidates = [("a.py", 1, "INV006")]
        live_counts = {"INV006": 40}

        result = _mass_invalidation_rules(candidates, live_counts)

        assert result == {}
