"""T-3675 (win32 round 18, Part 2): unit coverage for `frob.check`'s
`FROB_CHECK_STOP_BEFORE` debug knob -- the pipeline sender bisect that
brackets round-16/17's `executor.submit -> t.start()` interrupt stack
frame one stage at a time. Env-gated, OFF by default everywhere; only a
CI diag step (`.github/workflows/ci.yml`) sets it, one point per step.

Only `_check_stop_before`'s own gating logic is unit-tested here (its 4
call sites are exercised end to end by the CI diag steps themselves,
which real win32 CI is the only environment that can meaningfully run --
see docs/modules/process.md's "Round 18" paragraph)."""

from __future__ import annotations

from pathlib import Path

import pytest

import frob.check as check_mod
from frob.check import CheckResult, run_check


class TestCheckStopBefore:
    """`_check_stop_before` -- true exactly when `FROB_CHECK_STOP_BEFORE`
    equals the given point, checked fresh at each call."""

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestCheckStopBefore.test_false_when_env_uns\
    # et
    def test_false_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, raising=False)
        for point in check_mod._CHECK_STOP_POINTS:
            assert check_mod._check_stop_before(point) is False

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestCheckStopBefore.test_true_only_for_the_\
    # matching_point
    def test_true_only_for_the_matching_point(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, "tasks")
        results = {
            point: check_mod._check_stop_before(point)
            for point in check_mod._CHECK_STOP_POINTS
        }
        assert results == {
            "lock": False,
            "detect": False,
            "tasks": True,
            "submit": False,
        }

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestCheckStopBefore.test_unrecognized_value\
    # _matches_nothing
    def test_unrecognized_value_matches_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, "not-a-real-point")
        for point in check_mod._CHECK_STOP_POINTS:
            assert check_mod._check_stop_before(point) is False

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestCheckStopBefore.test_all_four_points_ar\
    # e_distinct_and_ordered
    def test_all_four_points_are_distinct_and_ordered(self) -> None:
        """Sanity-pins the exact 4-point set/order this ticket's CI diag
        sub-variants each name via FROB_CHECK_STOP_BEFORE=<point> -- a
        renamed/reordered/added point here without updating the workflow
        would silently desync the two."""
        assert check_mod._CHECK_STOP_POINTS == ("lock", "detect", "tasks", "submit")

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestCheckStopBefore.test_rejects_an_unknown\
    # _point_argument
    def test_rejects_an_unknown_point_argument(self) -> None:
        with pytest.raises(AssertionError):
            check_mod._check_stop_before("not-a-real-point")


class TestRunCheckHonorsStopBefore:
    """End-to-end: `run_check` itself actually short-circuits at each of
    the 4 named points instead of only `_check_stop_before` reporting
    true in isolation -- exercised against a bare `tmp_path` (no git
    init, no pyproject.toml), the same fixture shape `TestRunCheck.
    test_all_stages_skipped_returns_empty_result_for_root` in
    `test_check.py` already proves `run_check` tolerates."""

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore.test_lock_poin\
    # t_returns_empty_result_before_any_stage
    def test_lock_point_returns_empty_result_before_any_stage(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, "lock")
        result = run_check(tmp_path)
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore.test_tasks_poi\
    # nt_returns_empty_result_before_submit
    def test_tasks_point_returns_empty_result_before_submit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, "tasks")
        result = run_check(tmp_path)
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []

    # frob:tests \
    # tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore.test_no_stop_r\
    # equested_runs_normally
    def test_no_stop_requested_runs_normally(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control: with every stage skipped and no stop point set, the
        pre-existing skip-all-stages behavior (test_check.py's own
        TestRunCheck) is unaffected by this knob's presence."""
        monkeypatch.delenv(check_mod.FROB_CHECK_STOP_BEFORE_ENV, raising=False)
        result = run_check(
            tmp_path,
            skip_ruff=True,
            skip_ty=True,
            skip_arch=True,
            skip_cycle=True,
            skip_dup=True,
            skip_bind=True,
            skip_exports=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []
