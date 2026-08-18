"""Unit tests for `frob.verify._backpressure` (T-1692): bound the
unverified window by depth and age, and block a land at the ceiling."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.tickets._profile import ProfileName
from frob.verify._backpressure import (
    BackpressureCeilings,
    BackpressureError,
    block_until_watermark_advances,
    ceilings_for_profile,
    current_status,
    rapid_soft_warning,
    settings_for_profile,
)
from frob.verify._watermark import advance_watermark, record_intent
from tests.unit.verify.test_watermark import _init_git_repo_with_commits


# frob:waive WIRE001 reason="a private test-seed helper used only by this file's own \
# test methods below -- there is no production caller to wire it to by design, \
# mirroring tests/unit/verify/test_worker.py's identical _enqueue_n precedent" \
# permanent="true"
def _enqueue(root: Path, commit: str, *, ticket: str = "T-0001") -> None:
    result = record_intent(
        root,
        commit_sha=commit,
        ticket_id=ticket,
        touched_symbols=(f"a.py::{commit}",),
        profile="standard",
    )
    assert result.is_ok


class TestCeilingsForProfile:
    """Profile -> ceiling resolution: fortress is depth 0, rapid is
    unbounded, standard is a bounded default overridable via frob.toml."""

    def test_fortress_is_zero_depth_zero_age(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_fortress_is_zero_depth_zero_age  # noqa: E501
        ceilings = ceilings_for_profile(ProfileName.FORTRESS, tmp_path)
        assert ceilings.max_depth == 0
        assert ceilings.max_age_s == 0.0

    def test_rapid_is_unbounded(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_rapid_is_unbounded  # noqa: E501
        ceilings = ceilings_for_profile(ProfileName.RAPID, tmp_path)
        assert ceilings.max_depth is None
        assert ceilings.max_age_s is None

    def test_standard_default(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_standard_default  # noqa: E501
        ceilings = ceilings_for_profile(ProfileName.STANDARD, tmp_path)
        assert ceilings.max_depth is not None and ceilings.max_depth > 0
        assert ceilings.max_age_s is not None and ceilings.max_age_s > 0

    def test_standard_toml_override(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCeilingsForProfile.test_standard_toml_override  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            "[profile]\nbackpressure_max_depth = 2\nbackpressure_max_age_s = 10\n",
            encoding="utf-8",
        )
        ceilings = ceilings_for_profile(ProfileName.STANDARD, tmp_path)
        assert ceilings.max_depth == 2
        assert ceilings.max_age_s == 10.0


# frob:ticket T-2360
class TestSettingsForProfile:
    """T-2360: `settings_for_profile` must reproduce TODAY's if-rapid
    branch logic at each of the 5 measured call sites
    (`_land.py:2878`/`:3103`, `_land_cmd.py:4324`/`:4519`,
    `_evidence.py:323`, `_close_cmd.py:463`) exactly -- these tests
    assert against that CURRENT behavior, read from the live source at
    the time T-2360 was filed, not a guess."""

    # frob:ticket T-2360
    def test_fortress_matches_current_branch_logic(self) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_fortress_matches_current_branch_logic  # noqa: E501
        settings = settings_for_profile(ProfileName.FORTRESS)
        # None of the 5 branches distinguishes fortress from standard
        # today -- both take the "not rapid" arm at every site.
        assert settings.pre_commit_sweep_enabled is True
        assert settings.mutation_evidence_required is True
        assert settings.rel001_preflight_enabled is True
        assert settings.evidence_scope_unbound_is_debt is False

    # frob:ticket T-2360
    def test_standard_matches_current_branch_logic(self) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_standard_matches_current_branch_logic  # noqa: E501
        settings = settings_for_profile(ProfileName.STANDARD)
        assert settings.pre_commit_sweep_enabled is True
        assert settings.mutation_evidence_required is True
        assert settings.rel001_preflight_enabled is True
        assert settings.evidence_scope_unbound_is_debt is False

    # frob:ticket T-2360
    def test_rapid_matches_current_branch_logic(self) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_rapid_matches_current_branch_logic  # noqa: E501
        settings = settings_for_profile(ProfileName.RAPID)
        # _land_cmd.py:4324 -- rapid skips the pre-commit sweep (T-1575).
        assert settings.pre_commit_sweep_enabled is False
        # _land.py:3103 -- rapid skips TEST016 entirely (T-1575).
        assert settings.mutation_evidence_required is False
        # _close_cmd.py:463 -- rapid skips the REL001 preflight (T-1705).
        assert settings.rel001_preflight_enabled is False
        # _land.py:2878 / _evidence.py:323 -- rapid records the
        # evidence-scope-unbound finding as debt instead (T-1681).
        assert settings.evidence_scope_unbound_is_debt is True

    # frob:ticket T-2360
    def test_settings_are_frozen(self) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_settings_are_frozen  # noqa: E501
        settings = settings_for_profile(ProfileName.STANDARD)
        with pytest.raises(Exception):  # noqa: B017, PT011
            settings.pre_commit_sweep_enabled = False  # type: ignore[misc]

    # frob:ticket T-2360
    def test_unknown_profile_value_raises(self) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestSettingsForProfile.test_unknown_profile_value_raises  # noqa: E501
        with pytest.raises(ValueError, match="unrecognized ProfileName"):
            settings_for_profile("not-a-real-profile")


class TestCurrentStatus:
    """`current_status` reads the durable queue and decides whether
    either ceiling axis is tripped."""

    def test_empty_queue_is_never_tripped(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_empty_queue_is_never_tripped  # noqa: E501
        ceilings = BackpressureCeilings(max_depth=0, max_age_s=0.0)
        result = current_status(tmp_path, ceilings)
        assert result.is_ok
        status = result.danger_ok
        assert status.depth == 0
        assert status.age_s is None
        assert status.tripped is False

    def test_depth_ceiling_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_depth_ceiling_trips  # noqa: E501
        _enqueue(tmp_path, "c1")
        _enqueue(tmp_path, "c2")
        _enqueue(tmp_path, "c3")
        ceilings = BackpressureCeilings(max_depth=2, max_age_s=None)
        result = current_status(tmp_path, ceilings)
        assert result.is_ok
        status = result.danger_ok
        assert status.depth == 3
        assert status.tripped is True
        assert "depth" in status.reason

    def test_age_ceiling_trips(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_age_ceiling_trips  # noqa: E501
        _enqueue(tmp_path, "c1")
        ceilings = BackpressureCeilings(max_depth=None, max_age_s=1.0)
        # A clock reading far in the future makes the just-enqueued entry
        # look ancient, without a real sleep.
        result = current_status(tmp_path, ceilings, now_fn=lambda: 10_000_000_000.0)
        assert result.is_ok
        status = result.danger_ok
        assert status.tripped is True
        assert "age" in status.reason

    def test_unbounded_ceilings_never_trip(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_unbounded_ceilings_never_trip  # noqa: E501
        for i in range(50):
            _enqueue(tmp_path, f"c{i}")
        ceilings = BackpressureCeilings(max_depth=None, max_age_s=None)
        result = current_status(tmp_path, ceilings, now_fn=lambda: 10_000_000_000.0)
        assert result.is_ok
        assert result.danger_ok.tripped is False

    def test_queue_unreadable_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestCurrentStatus.test_queue_unreadable_is_an_error  # noqa: E501
        import frob.verify._backpressure as backpressure_mod
        from frob.verify._watermark import WatermarkError
        from typani.result import Err

        monkeypatch.setattr(
            backpressure_mod, "queue_status", lambda root: Err(WatermarkError.StoreCorrupt)
        )
        ceilings = BackpressureCeilings(max_depth=1, max_age_s=None)
        result = current_status(tmp_path, ceilings)
        assert result.is_err
        assert result.danger_err is BackpressureError.QueueUnreadable


class TestBlockUntilWatermarkAdvances:
    """The land-path entrypoint: block at the ceiling, drain to pay back
    the deferred cost, never silently."""

    def test_not_tripped_returns_immediately_without_draining(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_not_tripped_returns_immediately_without_draining  # noqa: E501
        calls: list[Path] = []
        ceilings = BackpressureCeilings(max_depth=5, max_age_s=None)
        result = block_until_watermark_advances(
            tmp_path, ceilings, "T-9000", drain_fn=lambda root: calls.append(root)
        )
        assert result.is_ok
        assert calls == []

    def test_tripped_drains_and_unblocks(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_tripped_drains_and_unblocks  # noqa: E501
        # K=2: a third queued entry trips depth. The injected drain_fn
        # simulates the coalescing worker going green: it advances the
        # watermark and compacts the queue, exactly what a real
        # `run_coalesced_verification` does on a genuinely clean batch.
        _enqueue(tmp_path, "c1")
        _enqueue(tmp_path, "c2")
        _enqueue(tmp_path, "c3")
        ceilings = BackpressureCeilings(max_depth=2, max_age_s=None)

        def _fake_drain(root: Path) -> None:
            from frob.verify._watermark import compact_queue

            advance_watermark(
                root, commit_sha="c3", run_id="run1", baseline_digest="deadbeef"
            )
            compact_queue(root)

        result = block_until_watermark_advances(
            tmp_path,
            ceilings,
            "T-9000",
            drain_fn=_fake_drain,
            poll_interval_s=0.0,
            sleep_fn=lambda s: None,
        )
        assert result.is_ok
        assert result.danger_ok.depth == 0
        assert result.danger_ok.tripped is False

    def test_persistently_red_batch_times_out(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_persistently_red_batch_times_out  # noqa: E501
        _enqueue(tmp_path, "c1")
        _enqueue(tmp_path, "c2")
        _enqueue(tmp_path, "c3")
        ceilings = BackpressureCeilings(max_depth=2, max_age_s=None)

        clock = {"t": 0.0}

        def _now() -> float:
            return clock["t"]

        def _sleep(seconds: float) -> None:
            clock["t"] += seconds + 1.0  # always past the poll interval

        result = block_until_watermark_advances(
            tmp_path,
            ceilings,
            "T-9000",
            drain_fn=lambda root: None,  # never actually drains anything
            poll_interval_s=1.0,
            timeout_s=5.0,
            now_fn=_now,
            sleep_fn=_sleep,
        )
        assert result.is_err
        assert result.danger_err is BackpressureError.BlockTimedOut

    def test_unbounded_ceiling_never_blocks(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_backpressure.py::TestBlockUntilWatermarkAdvances.test_unbounded_ceiling_never_blocks  # noqa: E501
        for i in range(100):
            _enqueue(tmp_path, f"c{i}")
        ceilings = BackpressureCeilings(max_depth=None, max_age_s=None)
        calls: list[Path] = []
        result = block_until_watermark_advances(
            tmp_path, ceilings, "T-9000", drain_fn=lambda root: calls.append(root)
        )
        assert result.is_ok
        assert calls == []


class TestRapidSoftWarning:
    """`rapid_soft_warning` (T-2290): the rapid profile's own soft
    ceiling -- never blocks, but names a message once real verification
    debt (measured via the real `git rev-list` commit gap, not the
    understating queue-entry depth) crosses a threshold."""

    def test_no_watermark_yet_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_backpressure.py::rapid_soft_warning kind="unit"
        assert rapid_soft_warning(tmp_path) is None

    def test_below_threshold_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_backpressure.py::rapid_soft_warning kind="unit"
        shas = _init_git_repo_with_commits(tmp_path, 2)
        advance_watermark(
            tmp_path, commit_sha=shas[0], run_id="r1", baseline_digest="d1"
        )
        assert rapid_soft_warning(tmp_path) is None

    def test_stale_watermark_trips_the_soft_warning(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_backpressure.py::rapid_soft_warning kind="unit"
        # A REAL multi-commit gap (12 commits), well past the default
        # soft-warning depth threshold -- the exact shape T-2290 measured
        # in this repo itself (403 raw commits behind a 6-day-old
        # watermark), not a synthetic one-commit gap.
        shas = _init_git_repo_with_commits(tmp_path, 12)
        advance_watermark(
            tmp_path, commit_sha=shas[0], run_id="r1", baseline_digest="d1"
        )
        warning = rapid_soft_warning(tmp_path)
        assert warning is not None
        assert "11" in warning
        assert "never blocks" in warning

    def test_toml_override(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_backpressure.py::rapid_soft_warning kind="unit"
        shas = _init_git_repo_with_commits(tmp_path, 3)
        advance_watermark(
            tmp_path, commit_sha=shas[0], run_id="r1", baseline_digest="d1"
        )
        (tmp_path / "frob.toml").write_text(
            "[profile]\nrapid_soft_warn_depth = 1\n", encoding="utf-8"
        )
        assert rapid_soft_warning(tmp_path) is not None
