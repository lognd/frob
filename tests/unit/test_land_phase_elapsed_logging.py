"""T-4417: `frob ticket land`'s phase-transition log lines carry an
elapsed-seconds prefix, so a slow land (T-4408: 50+ minutes, unattributable
to any phase without external `ps` inspection) is diagnosable from the
land log alone.
"""

from __future__ import annotations

import logging
import time

from frob.app.ticket_runner import _land_cmd


# frob:ticket T-4417
class TestLandPhaseElapsedLogging:
    """`_LandPhaseElapsedFilter`/`_land_phase_elapsed_seconds` (T-4417):
    one shared helper decorates every "ticket land: ..." log line with
    `[+<elapsed>s]`, rather than each of `_land_cmd.py`'s ~80 existing
    call sites computing its own elapsed time by hand."""

    # frob:ticket T-4417
    def setup_method(self) -> None:
        """Each test gets its own clock: T-4417's timer is a module
        global that lazily starts on the first phase line, so a prior
        test's elapsed baseline must never leak into the next one."""
        _land_cmd._land_phase_timer_start = None

    # frob:ticket T-4417
    def teardown_method(self) -> None:
        """Leave no timer state behind for tests outside this module."""
        _land_cmd._land_phase_timer_start = None

    # frob:ticket T-4417
    def test_elapsed_seconds_is_monotonic_across_phase_lines(self, caplog) -> None:
        """Two "ticket land: ..." lines a measurable gap apart must carry
        strictly increasing elapsed-seconds prefixes, and the very first
        one must start at (approximately) zero."""
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            _land_cmd._log.info("ticket land: %s phase one starting", "T-TEST")
            time.sleep(0.05)
            _land_cmd._log.info("ticket land: %s phase two starting", "T-TEST")

        messages = [r.getMessage() for r in caplog.records]
        assert len(messages) == 2
        assert messages[0].startswith("[+0.")
        assert "phase one starting" in messages[0]
        assert "phase two starting" in messages[1]

        first_elapsed = float(messages[0].split("[+")[1].split("s]")[0])
        second_elapsed = float(messages[1].split("[+")[1].split("s]")[0])
        assert second_elapsed > first_elapsed

    # frob:ticket T-4417
    def test_non_phase_log_lines_are_left_untouched(self, caplog) -> None:
        """A log line from this same logger that is NOT a "ticket land:
        ..." phase-transition line must pass through completely
        unmodified -- the filter's whole gate is the literal prefix
        match, and it must never decorate unrelated `_log` calls this
        package's other command modules (`_new_cmd`, `_close_cmd`, ...)
        share the logger name with."""
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            _land_cmd._log.info("ticket new: %s created", "T-TEST")

        messages = [r.getMessage() for r in caplog.records]
        assert messages == ["ticket new: T-TEST created"]

    # frob:ticket T-4417
    def test_elapsed_helper_starts_at_zero_on_first_call(self) -> None:
        """`_land_phase_elapsed_seconds` lazily starts its own clock on
        first call (no separate explicit "land began" call required from
        `_land`/`_land_core`), so the very first reading is ~0."""
        assert _land_cmd._land_phase_timer_start is None
        elapsed = _land_cmd._land_phase_elapsed_seconds()
        assert elapsed < 0.1
        assert _land_cmd._land_phase_timer_start is not None
