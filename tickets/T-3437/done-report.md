## Done report

T-3420 follow-up: fixed two regressions the touched-set run for T-3420 did not catch. (1) tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_declares_multiprocessing_and_sigterm still asserted the generated subprocess rc emits sigterm = True; fixed src/frob/testing/_coverage_refresh.py::_write_coverage_subprocess_rc to emit sigterm = False (matching pyproject.toml's own T-3420 setting -- one home for the decision) and rewrote both the generator's and the test's docstrings to cite T-3420/coveragepy#1101/#1340. Added test_rc_sigterm_matches_pyprojects_own_setting (designated repro, verified FAILED_AT_PARENT against the commit that adds it before the fix, PASSES at HEAD) as the genuine regression proof, since the pre-existing test changed its own expectation in the same commit as the fix and could never fail at main on its own. TestPyprojectDeclaresCoverageConcurrency's own sigterm assertion was already correctly False from T-3420. (2) tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_repeated_sigterm_terminates_in_bounded_time failed on macOS CI inside _send_signal_to_group: the child can legitimately have already exited before the second SIGTERM lands, raising ProcessLookupError (ESRCH) from os.killpg -- a dead process group IS the must-fire outcome (the process terminated, it did not deadlock), so ESRCH is now swallowed there instead of propagating as a test failure; no skip marker was added for macOS. MUST-FIRE verified: reverting sigterm to True locally makes both test_pyproject_declares_concurrency_and_sigterm and test_rc_sigterm_matches_pyprojects_own_setting fail. MUST-STAY-QUIET: tests/test_coverage.py (65 passed) and tests/system/test_coverage_sigterm.py (2 passed) pass on Linux locally with -p no:xdist and no skips added.

### Changed
```
 src/frob/testing/_coverage_refresh.py | 26 +++++++++++++++--------
 tests/system/test_coverage_sigterm.py | 21 ++++++++++++++++---
 tests/test_coverage.py                | 39 ++++++++++++++++++++++++++++++-----
 tickets/T-3437/ticket.md              | 26 ++++++++++++++++++++---
 4 files changed, 92 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_declares_multiprocessing_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestPyprojectDeclaresCoverageConcurrency::test_pyproject_declares_concurrency_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_repeated_sigterm_terminates_in_bounded_time` (pytest node id, verified passing when recorded)
- `tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_normal_run_writes_complete_coverage_data` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_sigterm_matches_pyprojects_own_setting` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 14 error(s), 4002 warning(s), 856 waived
- error-findings: AFFECT001@src/frob/testing/_coverage_refresh.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3437, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
