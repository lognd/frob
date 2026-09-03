"""T-3683 (win32 round 19, Part B): unit coverage for `tests/conftest.py`'s
mid-run watchdog -- gated on `FROB_TEST_MIDRUN_WATCHDOG_SECONDS`, the
third wedge-response mechanism this file carries (T-3608's xdist-only
crash-triggered stall watchdog, T-3675's session-finish hard-exit, and
now this one, which requires neither xdist nor a recorded crash: gated
purely on elapsed wall-clock time since the last observed test call-phase
report). Round-18 CI evidence (run 33582058515) measured the windows Test
step hitting its 1500s budget again with NO `FROB-TEST-HARD-EXIT:` line
printed at all -- the suite hangs BEFORE `pytest_sessionfinish`, which
T-3675's own hard-exit can never reach.

Only the pure gating/predicate/threshold-parsing logic is unit-tested
here (a real hard exit inside the test runner would kill it; `os._exit`
is monkeypatched to record its argument instead, same posture as
`test_conftest_hard_exit_guard.py`)."""

from __future__ import annotations

import pytest

from tests.unit._conftest_test_helpers import load_conftest_module


def _load_conftest():
    """Fresh standalone import of `tests/conftest.py` per test -- same
    posture as this ticket family's other conftest-module test files."""
    return load_conftest_module("_t3683_conftest_under_test")


class TestMidrunWatchdogThresholdS:
    """`_midrun_watchdog_threshold_s` -- `None` (disabled) unless the env
    var is a valid positive float."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS.test_none_when_unset  # noqa: E501
    def test_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.delenv(module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, raising=False)
        assert module._midrun_watchdog_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS.test_none_when_zero  # noqa: E501
    def test_none_when_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, "0")
        assert module._midrun_watchdog_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS.test_none_when_negative  # noqa: E501
    def test_none_when_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, "-5")
        assert module._midrun_watchdog_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS.test_none_when_not_numeric  # noqa: E501
    def test_none_when_not_numeric(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, "soon")
        assert module._midrun_watchdog_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS.test_parses_a_positive_value  # noqa: E501
    def test_parses_a_positive_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, "300")
        assert module._midrun_watchdog_threshold_s() == 300.0


class TestMidrunStallDetected:
    """`_midrun_stall_detected` -- pure elapsed-time predicate, no xdist
    or crash-marker dependency at all (unlike T-3608's `_stall_
    detected`)."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected.test_false_before_threshold_elapsed  # noqa: E501
    def test_false_before_threshold_elapsed(self) -> None:
        module = _load_conftest()
        assert module._midrun_stall_detected(100.0, 95.0, 10.0) is False

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected.test_true_at_exactly_the_threshold  # noqa: E501
    def test_true_at_exactly_the_threshold(self) -> None:
        module = _load_conftest()
        assert module._midrun_stall_detected(105.0, 95.0, 10.0) is True

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected.test_true_well_past_the_threshold  # noqa: E501
    def test_true_well_past_the_threshold(self) -> None:
        module = _load_conftest()
        assert module._midrun_stall_detected(1000.0, 95.0, 10.0) is True


class TestRunMidrunWatchdog:
    """`_run_midrun_watchdog` -- the background thread body: fires the
    hard-exit path exactly once when the predicate trips, and never when
    the stop event is set first."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdog.test_fires_hard_exit_when_no_progress_and_never_stopped  # noqa: E501
    def test_fires_hard_exit_when_no_progress_and_never_stopped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import threading

        module = _load_conftest()
        # No progress ever recorded; started_ts far in the past so the
        # very first poll already trips the predicate.
        module._last_progress_ts = None
        module._midrun_watchdog_started_ts = 0.0
        calls: list[tuple] = []
        monkeypatch.setattr(
            module,
            "_announce_midrun_stall_and_hard_exit",
            lambda config, now, threshold_s: calls.append((config, now, threshold_s)),
        )
        stop_event = threading.Event()
        # threshold_s=0.01 with a started_ts of 0.0 (epoch) guarantees an
        # immediate trip on the thread's own first wait() return -- but
        # since we call the target function directly (not via a real
        # thread), the loop runs synchronously and returns after firing
        # once.
        module._run_midrun_watchdog(
            config=None, stop_event=stop_event, threshold_s=0.01
        )
        assert len(calls) == 1

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdog.test_never_fires_once_stop_event_is_set  # noqa: E501
    def test_never_fires_once_stop_event_is_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import threading

        module = _load_conftest()
        calls: list[tuple] = []
        monkeypatch.setattr(
            module,
            "_announce_midrun_stall_and_hard_exit",
            lambda config, now, threshold_s: calls.append((config, now, threshold_s)),
        )
        stop_event = threading.Event()
        stop_event.set()
        module._run_midrun_watchdog(
            config=None, stop_event=stop_event, threshold_s=0.01
        )
        assert calls == []


class TestTotalBudgetThresholdS:
    """`_total_budget_threshold_s` (T-3707) -- same parse/validate shape
    as `_midrun_watchdog_threshold_s`, its sibling env var."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetThresholdS.test_none_when_unset  # noqa: E501
    def test_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.delenv(module.FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, raising=False)
        assert module._total_budget_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetThresholdS.test_none_when_zero  # noqa: E501
    def test_none_when_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, "0")
        assert module._total_budget_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetThresholdS.test_none_when_not_numeric  # noqa: E501
    def test_none_when_not_numeric(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, "soon")
        assert module._total_budget_threshold_s() is None

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetThresholdS.test_parses_a_positive_value  # noqa: E501
    def test_parses_a_positive_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _load_conftest()
        monkeypatch.setenv(module.FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, "1200")
        assert module._total_budget_threshold_s() == 1200.0


class TestTotalBudgetExceeded:
    """`_total_budget_exceeded` (T-3707) -- pure elapsed-time predicate
    with no progress signal, unlike `_midrun_stall_detected`."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded.test_false_before_budget_elapsed  # noqa: E501
    def test_false_before_budget_elapsed(self) -> None:
        module = _load_conftest()
        assert module._total_budget_exceeded(100.0, 0.0, 200.0) is False

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded.test_true_at_exactly_the_budget  # noqa: E501
    def test_true_at_exactly_the_budget(self) -> None:
        module = _load_conftest()
        assert module._total_budget_exceeded(200.0, 0.0, 200.0) is True

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded.test_true_well_past_the_budget  # noqa: E501
    def test_true_well_past_the_budget(self) -> None:
        module = _load_conftest()
        assert module._total_budget_exceeded(10_000.0, 0.0, 200.0) is True


class TestRunMidrunWatchdogTotalBudget:
    """`_run_midrun_watchdog` with `total_budget_s` armed (T-3707) --
    fires the TOTAL-BUDGET hard-exit even while the suite is still
    making progress (no stall), and independent of whether a stall
    threshold is armed at all."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdogTotalBudget.test_fires_total_budget_exit_with_no_stall_threshold_armed  # noqa: E501
    def test_fires_total_budget_exit_with_no_stall_threshold_armed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import threading
        import time

        module = _load_conftest()
        # Simulate continuous progress: _last_progress_ts is "now", so
        # the stall predicate (if it were armed) would never trip -- only
        # the total-budget trigger can fire here.
        module._last_progress_ts = time.time()
        module._midrun_watchdog_started_ts = 0.0
        calls: list[tuple] = []
        monkeypatch.setattr(
            module,
            "_announce_total_budget_exceeded_and_hard_exit",
            lambda config, now, started_ts, budget_s: calls.append(
                (config, now, started_ts, budget_s)
            ),
        )
        stop_event = threading.Event()
        module._run_midrun_watchdog(
            config=None,
            stop_event=stop_event,
            threshold_s=None,
            total_budget_s=0.01,
        )
        assert len(calls) == 1
        assert calls[0][3] == 0.01

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdogTotalBudget.test_never_fires_when_total_budget_not_armed  # noqa: E501
    def test_never_fires_when_total_budget_not_armed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import threading

        module = _load_conftest()
        calls: list[int] = []
        monkeypatch.setattr(
            module,
            "_announce_total_budget_exceeded_and_hard_exit",
            lambda config, now, started_ts, budget_s: calls.append(1),
        )
        stop_event = threading.Event()
        stop_event.set()
        module._run_midrun_watchdog(
            config=None,
            stop_event=stop_event,
            threshold_s=None,
            total_budget_s=None,
        )
        assert calls == []


class TestEmitHardExitLines:
    """`_emit_hard_exit_lines` (T-3726) -- the shared tail every
    `_announce_*_and_hard_exit` in `tests/conftest.py` now delegates to.
    Root cause this guards: a local repro (short FROB_TEST_TOTAL_BUDGET_
    SECONDS + a sleeping test, run for real under a real pytest
    subprocess with fd-level capturing active) showed the SUITE-RESULT
    line silently swallowed even though `reporter.write_line` raised no
    exception and `sys.stdout.flush()` ran -- pytest's own
    `CaptureManager` (method='fd') was still capturing the real stdout
    fd, so the write landed in ITS tmpfile, not the terminal/redirect
    target `os._exit` then never gave a chance to flush back out. These
    tests assert the fix's mechanism directly: `capturemanager.
    suspend_global_capture` is called before any line is written."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestEmitHardExitLines.test_suspends_global_capture_before_writing_when_capman_present  # noqa: E501
    def test_suspends_global_capture_before_writing_when_capman_present(self) -> None:
        module = _load_conftest()
        events: list[str] = []

        class _FakeCapman:
            def suspend_global_capture(self, in_: bool = False) -> None:
                events.append("suspend")

        class _FakeReporter:
            def write_line(self, line: str) -> None:
                events.append(f"write:{line}")

        capman = _FakeCapman()
        reporter = _FakeReporter()

        class _FakeConfig:
            class pluginmanager:  # noqa: N801 -- mirrors pytest.Config's own shape
                @staticmethod
                def get_plugin(name: str) -> object:
                    return {"capturemanager": capman, "terminalreporter": reporter}[
                        name
                    ]

        module._emit_hard_exit_lines(_FakeConfig(), ["hello", "world"])
        assert events == ["suspend", "write:hello", "write:world"], (
            "suspend_global_capture must run BEFORE any write, or the "
            "write can still land in the captured tmpfile"
        )

    # frob:tests \
    # tests/unit/test_conftest_midrun_watchdog.py::TestEmitHardExitLines.test_never_rai\
    # ses_when_capman_absent
    def test_never_raises_when_capman_absent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module = _load_conftest()

        class _FakeConfig:
            class pluginmanager:  # noqa: N801 -- mirrors pytest.Config's own shape
                @staticmethod
                def get_plugin(name: str) -> None:
                    return None

        module._emit_hard_exit_lines(_FakeConfig(), ["a line"])
        assert "a line" in capsys.readouterr().out

    # frob:tests \
    # tests/unit/test_conftest_midrun_watchdog.py::TestEmitHardExitLines.test_a_suspend\
    # _exception_never_blocks_the_write
    def test_a_suspend_exception_never_blocks_the_write(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module = _load_conftest()

        class _RaisingCapman:
            def suspend_global_capture(self, in_: bool = False) -> None:
                raise RuntimeError("no active global capturing")

        class _FakeConfig:
            class pluginmanager:  # noqa: N801 -- mirrors pytest.Config's own shape
                @staticmethod
                def get_plugin(name: str) -> object | None:
                    if name == "capturemanager":
                        return _RaisingCapman()
                    return None

        module._emit_hard_exit_lines(_FakeConfig(), ["still printed"])
        assert "still printed" in capsys.readouterr().out


class TestAnnounceTotalBudgetExceededAndHardExit:
    """`_announce_total_budget_exceeded_and_hard_exit` (T-3707) --
    os._exit is monkeypatched to record its argument instead of really
    exiting, same posture as its stall-watchdog sibling test."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceTotalBudgetExceededAndHardExit.test_hard_exits_with_status_1_and_prints_the_inventory_line  # noqa: E501
    def test_hard_exits_with_status_1_and_prints_the_inventory_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module = _load_conftest()
        calls: list[int] = []
        monkeypatch.setattr(module.os, "_exit", calls.append)

        class _FakeConfig:
            class pluginmanager:  # noqa: N801 -- mirrors pytest.Config's own shape
                @staticmethod
                def get_plugin(name: str) -> None:
                    return None

        module._announce_total_budget_exceeded_and_hard_exit(
            _FakeConfig(), 1250.0, 0.0, 1200.0
        )
        assert calls == [1]
        out = capsys.readouterr().out
        assert "SUITE-RESULT: TOTAL-BUDGET-EXCEEDED" in out
        assert "FROB-TEST-HARD-EXIT:" in out


class TestAnnounceMidrunStallAndHardExit:
    """`_announce_midrun_stall_and_hard_exit` -- os._exit is
    monkeypatched to record its argument instead of really exiting."""

    # frob:tests tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceMidrunStallAndHardExit.test_hard_exits_with_status_1_and_prints_the_inventory_line  # noqa: E501
    def test_hard_exits_with_status_1_and_prints_the_inventory_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        module = _load_conftest()
        calls: list[int] = []
        monkeypatch.setattr(module.os, "_exit", calls.append)

        class _FakeConfig:
            class pluginmanager:  # noqa: N801 -- mirrors pytest.Config's own shape
                @staticmethod
                def get_plugin(name: str) -> None:
                    return None

        module._announce_midrun_stall_and_hard_exit(_FakeConfig(), 100.0, 10.0)
        assert calls == [1]
        out = capsys.readouterr().out
        assert "SUITE-RESULT: MIDRUN-WATCHDOG-STALL" in out
        assert "FROB-TEST-HARD-EXIT:" in out
