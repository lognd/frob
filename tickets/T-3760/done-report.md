## Done report

win32 CI fails these tests because TestReapOrphanedForkservers and TestCountRunningChecks exercise /proc/<pid>/stat and /proc/<pid>/cmdline directly (forkserver age/ppid checks, check-process argv scan) -- genuinely POSIX-only primitives with no Windows equivalent. Added skipif(sys.platform==win32) at the narrowest correct level (method for the two TestReapOrphanedForkservers tests, class for TestCountRunningChecks since all three methods there are equally /proc-dependent). Verified on Linux: all 44 tests in the file still pass (skips don't fire here).

### Changed
```
 tests/unit/test_process_reap.py | 18 ++++++++++++++++++
 tickets/T-3760/ticket.md        |  8 +++++++-
 2 files changed, 25 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_forkserver_of_orphaned_forkserver_is_reaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_counts_other_check_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_excludes_self` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestCountRunningChecks::test_ignores_non_check_processes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4315 warning(s), 919 waived
- error-findings: COV003@tests/test_ci_workflow_matrix.py
