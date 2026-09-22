"""T-3993, F-209: ledger verbs that write one file ran for minutes in
silence, so the harness backgrounded them and an agent reported finished
work as still "waiting". `_report_phase_progress` narrates which phase a
slow `frob ticket new` is in once the command has already run past
`_PHASE_PROGRESS_THRESHOLD_S`, and stays silent on the fast common case
(MUST-STAY-QUIET)."""

from __future__ import annotations

import logging
import time

from frob.app.ticket_runner._new import (
    _PHASE_PROGRESS_THRESHOLD_S,
    _report_phase_progress,
)


# frob:ticket T-3993
class TestPhaseProgress:
    """`_report_phase_progress`'s threshold behaviour: quiet under the
    threshold, one INFO line naming the phase once it is crossed, and
    always quiet with no command-wide clock (`start_time=None`)."""

    # frob:tests src/frob/app/ticket_runner/_new.py::_report_phase_progress  # noqa: E501
    def test_fast_run_stays_quiet(self, caplog) -> None:  # noqa: ANN001
        """A run well under `_PHASE_PROGRESS_THRESHOLD_S` emits nothing --
        the fast common case must not spam phase lines (MUST-STAY-QUIET)."""
        caplog.set_level(logging.INFO, logger="frob.app.ticket_runner")
        start_time = time.monotonic()
        _report_phase_progress("ticket new", start_time, "a fast phase")
        assert caplog.records == []
# frob:tests src/frob/app/ticket_runner/_new.py::_report_phase_progress  # noqa: E501

    def test_slow_run_names_the_phase(self, caplog) -> None:  # noqa: ANN001
        """A run already past the threshold logs one INFO line that names
        the phase -- the MUST-FIRE fixture."""
        caplog.set_level(logging.INFO, logger="frob.app.ticket_runner")
        start_time = time.monotonic() - (_PHASE_PROGRESS_THRESHOLD_S + 1.0)
        _report_phase_progress("ticket new", start_time, "a slow phase")
        assert len(caplog.records) == 1
        assert "a slow phase" in caplog.records[0].message

    # frob:tests src/frob/app/ticket_runner/_new.py::_report_phase_progress  # noqa: E501
    def test_no_clock_stays_quiet(self, caplog) -> None:  # noqa: ANN001
        """`start_time=None` (a caller with no command-wide clock, e.g. an
        isolated unit test) never emits progress."""
        caplog.set_level(logging.INFO, logger="frob.app.ticket_runner")
        _report_phase_progress("ticket new", None, "any phase")
        assert caplog.records == []
