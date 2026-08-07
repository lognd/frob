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
)
from frob.verify._watermark import advance_watermark, record_intent


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
