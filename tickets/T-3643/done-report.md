## Done report

T-3608's stall watchdog added the xdist-only hook pytest_testnodedown to
tests/conftest.py without @pytest.hookimpl(optionalhook=True). Windows
CI's Test step runs -p no:xdist, so pytest's own plugin validation
refused to start the session at all: PluginValidationError: unknown hook
'pytest_testnodedown' in plugin tests.conftest, SUITE-RESULT: DID-NOT-
COMPLETE exitstatus=3, collected=0 -- the entire Windows suite dead
before a single test ran (run 33491468339). Fix: added the decorator,
matching this file's pre-existing pytest_handlecrashitem waiver's same
optionalhook posture. Audited every other pytest_* hook in this file --
pytest_configure/pytest_internalerror/pytest_runtest_logreport/
pytest_runtest_logstart/pytest_runtest_logfinish/pytest_sessionfinish/
pytest_collection_modifyitems are all standard pytest core hookspecs
(fire under plain serial pytest too, by design -- several of them are
explicitly no-ops there per their own docstrings), not xdist-only, so
none of them needed this decorator.

Verified: pytest -p no:xdist --collect-only -q tests/ now returns
exitstatus=0 collected=13156 (was a hard PluginValidationError crash
before this fix) -- the only warnings are the pre-existing, already-
documented PytestUnknownMarkWarning for xdist_group markers under plain
pytest, unrelated to this hook. tests/unit/test_conftest_stackdump.py
(30 tests, including the watchdog's own integration test that actually
simulates a worker crash) is clean under xdist -- the watchdog itself is
completely unchanged and still fires correctly (loud STALL-DETECTED
abort), per the ticket's explicit instruction not to weaken it.

Evidence: a new test_pytest_testnodedown_is_optionalhook pins the
decorator itself (reads pytest_impl off the hook function, asserts
optionalhook=True) so a future edit cannot silently drop it again;
test_testnodedown_marks_a_death_controller_only (pre-existing) pins the
hook's actual controller-only behavior is unaffected by the decorator.

Gates: ruff-check/ruff-format clean on both touched files; gate:SCOPE
clean. The repo-wide ruff-format/gate:DRIFT/etc FAILs frob check reports
are pre-existing and unattributable to this diff (scope-note: --ticket
scopes only SCOPE/PREWORK/diff-driven COV/FMT/AFFECT; verified separately
that ruff format --check on just this ticket's two files passes).

Filed: none new.

### Changed
```
 tests/conftest.py                     | 16 +++++++++++++++-
 tests/unit/test_conftest_stackdump.py | 21 +++++++++++++++++++++
 tickets/T-3643/ticket.md              |  5 ++++-
 3 files changed, 40 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestStallWatchdog::test_pytest_testnodedown_is_optionalhook` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestStallWatchdog::test_testnodedown_marks_a_death_controller_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 4226 warning(s), 898 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/process/_guard.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT002@src/frob/vet/_capability_core.py, DRIFT002@src/frob/vet/_capability_python.py, DRIFT002@src/frob/vet/_capability_scan.py, DRIFT002@src/frob/vet/_supplychain.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3643, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
