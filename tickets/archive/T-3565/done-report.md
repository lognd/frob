## Done report

Changed:
- tests/conftest.py::_install_sigbreak_faulthandler
- tests/unit/test_conftest_sigbreak_faulthandler.py (new)

Run 33370059331 (windows-latest, after T-3560 landed) crashed
pytest_configure itself with INTERNALERROR AttributeError: module
'faulthandler' has no attribute 'register' -- faulthandler.register is
POSIX-only in CPython and does not exist at all on win32 builds, not
merely a degraded no-op there. Replaced the unconditional
faulthandler.register call with a signal.signal(SIGBREAK, handler)
fallback whose handler calls faulthandler.dump_traceback(all_threads=True)
then chains to the previously-installed SIGBREAK handler -- preserving
the original "observation-only, never changes how the interrupt itself
is handled" contract. Kept a hasattr(faulthandler, "register") branch
for a hypothetical future platform where both exist, though none does
today.

Added tests/unit/test_conftest_sigbreak_faulthandler.py: deliberately
NOT gated by a win32-only module skip (unlike test_conftest_stackdump.py's
SIGUSR1 coverage) -- it simulates the exact win32 + register-absent
shape via monkeypatch from Linux/macOS CI, so this crash class is
caught before ever reaching a live Windows job again. 6 tests: the
regression itself (must not raise), the fallback genuinely installs a
signal handler, the handler dumps-then-chains to the previous handler,
the register path is still preferred when available, and the two
pre-existing no-op guards (off win32, no SIGBREAK attribute) are
unchanged.

Evidence:
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::{test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32,test_installs_a_signal_handler_when_register_is_absent,test_dump_then_chain_calls_dump_traceback_then_previous_handler,test_still_prefers_faulthandler_register_when_it_exists,test_noop_off_win32,test_noop_when_no_sigbreak_attribute} (pytest node ids, verified passing)

Filed: none

Gates: `uv run pytest -p no:xdist tests/unit/test_conftest_sigbreak_faulthandler.py`
(6 passed) plus `tests/unit/test_conftest_stackdump.py` and
`tests/unit/test_conftest_color_env.py` (27 passed, confirming no
regression to the sibling SIGUSR1/color-env conftest coverage). Scoped
`frob check --ticket T-3565 --only affect_drift --only coverage --only
fmt` clean on this ticket's own touched-set concerns (no
AFFECT001/COV002/TODO001/FMT001 against either touched file).
