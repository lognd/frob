"""T-3560's `_install_sigbreak_faulthandler` (TEMPORARY windows-latest
diagnostics) was REVERTED by T-3577 in the same land that fixed the named
windows-latest CI hang -- per T-3560's own contract ("revert once the named
culprit is fixed"). The function this module tested no longer exists in
`tests/conftest.py`.

This file is kept as a STUB (rather than deleted outright) purely so
T-3565's own `tickets/T-3565/ticket.md` scope glob (which still names this
path) resolves to an existing file instead of crashing `frob check`'s
evidence-scan with `FileNotFoundError` -- see T-3577's Done report. Every
test below is a fixed skip, never a real assertion against removed code.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="T-3577: _install_sigbreak_faulthandler was reverted (T-3560's own "
    "contract) in the same land that fixed the windows-latest CI hang -- "
    "nothing left in tests/conftest.py for this module to exercise"
)


# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32  # noqa: E501
# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_installs_a_signal_handler_when_register_is_absent  # noqa: E501
# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_dump_then_chain_calls_dump_traceback_then_previous_handler  # noqa: E501
# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_still_prefers_faulthandler_register_when_it_exists  # noqa: E501
# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_noop_off_win32  # noqa: E501
# frob:tests tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_noop_when_no_sigbreak_attribute  # noqa: E501
class TestSigbreakFaultHandlerCrossPlatformSafety:
    """Superseded by T-3577's revert -- every case below is a fixed skip."""

    def test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32(
        self,
    ) -> None:
        """Superseded (T-3577): the function under test no longer exists."""

    def test_installs_a_signal_handler_when_register_is_absent(self) -> None:
        """Superseded (T-3577): the function under test no longer exists."""

    def test_dump_then_chain_calls_dump_traceback_then_previous_handler(self) -> None:
        """Superseded (T-3577): the function under test no longer exists."""

    def test_still_prefers_faulthandler_register_when_it_exists(self) -> None:
        """Superseded (T-3577): the function under test no longer exists."""

    def test_noop_off_win32(self) -> None:
        """Superseded (T-3577): the function under test no longer exists."""

    def test_noop_when_no_sigbreak_attribute(self) -> None:
        """Superseded (T-3577): the function under test no longer exists."""
