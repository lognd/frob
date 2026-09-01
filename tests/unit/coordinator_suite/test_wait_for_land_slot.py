import pytest

from tests.unit.conftest import (
    wait_for_land_slot,
)


# frob:ticket T-2775
class TestWaitForSlot:
    """`wait_for_land_slot.wait_for_slot` -- the polling state machine.
    `probe_lands_in_flight` itself is monkeypatched here (not
    `subprocess.run`) so each case can script an exact sequence of
    readings over successive ticks without real subprocess semantics."""

    def _fake_clock(self):
        """A fake `now`/`sleep` pair advancing in lockstep so the state
        machine's own elapsed-time math runs deterministically with zero
        real wall-clock waiting."""
        state = {"t": 0.0}

        def now() -> float:
            return state["t"]

        def sleep(seconds: float) -> None:
            state["t"] += seconds

        return now, sleep

    def test_slot_already_free_returns_immediately(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 0)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert "slot free" in summary
        # POSITIVE CONTROL: the common uncontended case must not impose a
        # fixed sleep -- zero time should have elapsed.
        assert now() == 0.0

    def test_land_in_flight_then_free_blocks_then_returns(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POSITIVE CONTROL (T-2775): with a land genuinely in flight the
        script BLOCKS (does not return 0 early) until it later clears."""
        readings = iter([2, 2, 1, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert now() == 30.0  # blocked through 3 non-qualifying polls

    def test_always_in_flight_times_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 5)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_TIMEOUT
        assert "timeout" in summary
        assert "last measured LANDS IN FLIGHT=5" in summary

    def test_always_unmeasurable_never_returns_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POSITIVE CONTROL (T-2775), the one the ticket names as the
        proof that matters: the status probe is forced to fail on EVERY
        poll. The script must exit with the measurement-failure code and
        NOT 0 -- an unmeasurable fleet must never be mistaken for a free
        slot."""
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: None
        )
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_MEASUREMENT_FAILED
        assert code != wait_for_land_slot.EXIT_SLOT_FREE
        assert "measurement failed" in summary

    def test_measured_then_unmeasurable_is_timeout_not_measurement_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Once ANY real reading was obtained, later probe failures must
        not retroactively turn a genuine (if incomplete) measurement into
        MEASUREMENT_FAILED -- that would hide the fact that a land really
        was observed in flight."""
        readings = iter([3, None, None, None, None])

        def fake_probe(cmd):
            try:
                return next(readings)
            except StopIteration:
                return None

        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", fake_probe)
        now, sleep = self._fake_clock()
        code, summary = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=40,
            poll_interval_s=10,
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_TIMEOUT
        assert "last measured LANDS IN FLIGHT=3" in summary

    def test_verbose_tick_hook_receives_every_reading(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        readings = iter([2, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        now, sleep = self._fake_clock()
        seen: list[int | None] = []
        code, _ = wait_for_land_slot.wait_for_slot(
            command=["irrelevant"],
            max_in_flight=0,
            timeout_s=100,
            poll_interval_s=10,
            on_tick=lambda reading, elapsed: seen.append(reading),
            sleep=sleep,
            now=now,
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        assert seen == [2, 0]


# frob:ticket T-2775
class TestWaitForLandSlotMain:
    """`wait_for_land_slot.main` -- the CLI wrapper: exactly one summary
    line to stdout, `--verbose` adds per-tick lines to stderr, and
    `--fleet-status-cmd` is the fault-injection seam a caller (or this
    ticket's own required positive control) uses to force a real,
    end-to-end measurement failure without touching the live fleet."""

    def test_quiet_by_default_prints_one_summary_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(wait_for_land_slot, "probe_lands_in_flight", lambda cmd: 0)
        code = wait_for_land_slot.main(["--timeout", "5"])
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert out.out.strip().count("\n") == 0
        assert "slot free" in out.out
        assert out.err == ""

    def test_verbose_adds_per_tick_lines_to_stderr(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        readings = iter([1, 0])
        monkeypatch.setattr(
            wait_for_land_slot, "probe_lands_in_flight", lambda cmd: next(readings)
        )
        code = wait_for_land_slot.main(
            ["--timeout", "5", "--poll-interval", "1", "--verbose"]
        )
        assert code == wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert out.out.strip().count("\n") == 0
        assert "LANDS IN FLIGHT=1" in out.err
        assert "LANDS IN FLIGHT=0" in out.err

    def test_end_to_end_forced_probe_failure_via_fleet_status_cmd(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """POSITIVE CONTROL (T-2775), end-to-end through the real CLI and
        real `subprocess.run` (no monkeypatching of `probe_lands_in_flight`
        itself): `--fleet-status-cmd` points at a command that always
        fails, proving the wiring from CLI flag through to the
        measurement-failure exit code with nothing stubbed out."""
        code = wait_for_land_slot.main(
            [
                "--timeout",
                "2",
                "--poll-interval",
                "1",
                "--fleet-status-cmd",
                "false",
            ]
        )
        assert code == wait_for_land_slot.EXIT_MEASUREMENT_FAILED
        assert code != wait_for_land_slot.EXIT_SLOT_FREE
        out = capsys.readouterr()
        assert "measurement failed" in out.out
