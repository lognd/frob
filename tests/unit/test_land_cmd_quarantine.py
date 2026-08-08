"""Unit tests for `frob.app.ticket_runner._land_cmd._quarantine_override_
ceilings` (T-1693): while quarantine is raised, deferred landing is
forced synchronous regardless of the land's own profile."""

from __future__ import annotations

from pathlib import Path

from frob.app.ticket_runner._land_cmd import (
    _auto_clear_synthetic_quarantine,
    _quarantine_override_ceilings,
    _raise_quarantine_on_persistent_block_timeout,
)
from frob.verify._backpressure import BackpressureCeilings
from frob.verify._quarantine import (
    QuarantinedFinding,
    is_quarantined,
    load_quarantine,
    raise_quarantine,
)
from frob.verify._watermark import record_intent


# frob:ticket T-1693
class TestQuarantineOverrideCeilings:
    # frob:ticket T-1693
    def test_not_quarantined_is_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_not_quarantined_is_unchanged  # noqa: E501
        original = BackpressureCeilings(max_depth=5, max_age_s=3600.0)
        result = _quarantine_override_ceilings(tmp_path, original, ticket_id="T-0001")
        assert result is original

    # frob:ticket T-1693
    def test_quarantined_forces_synchronous(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_quarantined_forces_synchronous  # noqa: E501
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        ).is_ok

        original = BackpressureCeilings(max_depth=None, max_age_s=None)  # rapid's own
        result = _quarantine_override_ceilings(tmp_path, original, ticket_id="T-0001")
        assert result == BackpressureCeilings(max_depth=0, max_age_s=0.0)

    # frob:ticket T-1693
    def test_corrupt_store_also_forces_synchronous(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings.test_corrupt_store_also_forces_synchronous  # noqa: E501
        path = tmp_path / ".frob" / "quarantine.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")

        original = BackpressureCeilings(max_depth=None, max_age_s=None)
        result = _quarantine_override_ceilings(tmp_path, original, ticket_id="T-0001")
        assert result == BackpressureCeilings(max_depth=0, max_age_s=0.0)


# frob:ticket T-1693
class TestRaiseQuarantineOnPersistentBlockTimeout:
    # frob:ticket T-1693
    def test_raises_with_a_synthetic_finding(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestRaiseQuarantineOnPersistentBlockTimeout.test_raises_with_a_synthetic_finding  # noqa: E501
        assert is_quarantined(tmp_path).danger_ok is False
        _raise_quarantine_on_persistent_block_timeout(tmp_path, "T-0001")
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_already_quarantined_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestRaiseQuarantineOnPersistentBlockTimeout.test_already_quarantined_is_a_noop  # noqa: E501
        original = raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(QuarantinedFinding(rule_id="TEST001", file="src/x.py", line=1),),
        )
        assert original.is_ok
        _raise_quarantine_on_persistent_block_timeout(tmp_path, "T-0001")
        # The richer, already-recorded finding set must survive --
        # the coarser synthetic finding must not have overwritten it.
        from frob.verify._quarantine import load_quarantine

        reloaded = load_quarantine(tmp_path)
        assert reloaded.is_ok
        reloaded_record = reloaded.danger_ok
        original_record = original.danger_ok
        assert reloaded_record is not None
        assert original_record is not None
        assert reloaded_record.findings == original_record.findings


# frob:ticket T-1693
class TestAutoClearSyntheticQuarantine:
    """`_auto_clear_synthetic_quarantine`: the ONE case a land auto-
    clears a raised quarantine -- every finding is this same module's
    own synthetic `BACKPRESSURE_TIMEOUT` marker, never a real T-1690
    attribution, AND the underlying condition has resolved."""

    _CEILINGS = BackpressureCeilings(max_depth=0, max_age_s=None)

    # frob:ticket T-1693
    def test_no_quarantine_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_no_quarantine_is_a_noop  # noqa: E501
        _auto_clear_synthetic_quarantine(tmp_path, self._CEILINGS)
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-1693
    def test_real_attributed_finding_never_auto_clears(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_real_attributed_finding_never_auto_clears  # noqa: E501
        assert raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(
                QuarantinedFinding(
                    rule_id="TEST001",
                    file="src/x.py",
                    line=1,
                    commit_sha="deadbeef",
                    ticket_id="T-1000",
                ),
            ),
        ).is_ok
        # Empty queue -- current_status would read "not tripped" -- but a
        # REAL attributed finding must never auto-clear regardless.
        _auto_clear_synthetic_quarantine(tmp_path, self._CEILINGS)
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_synthetic_finding_stays_raised_while_still_tripped(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_synthetic_finding_stays_raised_while_still_tripped  # noqa: E501
        _raise_quarantine_on_persistent_block_timeout(tmp_path, "T-0001")
        assert record_intent(
            tmp_path,
            commit_sha="stillqueued",
            ticket_id="T-0002",
            touched_symbols=("src/x.py::foo",),
            profile="standard",
        ).is_ok
        # max_depth=0 -- ANY queued entry trips it.
        _auto_clear_synthetic_quarantine(tmp_path, self._CEILINGS)
        assert is_quarantined(tmp_path).danger_ok is True

    # frob:ticket T-1693
    def test_synthetic_finding_clears_once_status_is_untripped(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_quarantine.py::TestAutoClearSyntheticQuarantine.test_synthetic_finding_clears_once_status_is_untripped  # noqa: E501
        _raise_quarantine_on_persistent_block_timeout(tmp_path, "T-0001")
        # An empty queue never trips max_depth=0.
        _auto_clear_synthetic_quarantine(tmp_path, self._CEILINGS)
        assert is_quarantined(tmp_path).danger_ok is False
        cleared = load_quarantine(tmp_path).danger_ok
        assert cleared is not None
        assert cleared.cleared_reason is not None
        assert cleared.findings[0].disposition == "dismissed"
