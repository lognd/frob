## Done report

Sweep flagged unresolved-attribute against tests/system/test_coverage_sigterm.py:189 (ty, [platform=win32] Module signal has no member SIGKILL, attributed to T-3420). Fixed by routing signal.SIGKILL through a getattr guard (_SIGKILL: int = getattr(signal, 'SIGKILL', signal.SIGTERM)), the same idiom _send_signal_to_group already uses for os.killpg. Static-analysis-only fix (frob:no-behavior-change): the test class is already skipif(win32)'d at runtime, so this changes no runtime behavior on any platform this suite actually runs on -- confirmed frob check --only ty no longer reports the finding, and both tests in the file still pass.

### Changed
```
 tests/system/test_coverage_sigterm.py | 13 ++++++++++++-
 tickets/T-3431/ticket.md              | 19 +++++++++++++++++--
 2 files changed, 29 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_repeated_sigterm_terminates_in_bounded_time` (pytest node id, verified passing when recorded)
- `tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_normal_run_writes_complete_coverage_data` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 13 error(s), 3968 warning(s), 857 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
