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
        monkeypatch.delenv(
            module.FROB_TEST_MIDRUN_WATCHDOG_SECONDS_ENV, raising=False
        )
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
        module._run_midrun_watchdog(config=None, stop_event=stop_event, threshold_s=0.01)
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
        module._run_midrun_watchdog(config=None, stop_event=stop_event, threshold_s=0.01)
        assert calls == []


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
