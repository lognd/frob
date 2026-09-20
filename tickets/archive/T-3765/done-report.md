## Done report

win32 CI fails these tests because starttime is read via /proc/<pid>/stat, which the module's own docstring says is Linux-specific (/proc is not portable) -- genuinely POSIX-only. Added skipif(sys.platform==win32) on both module-level test functions. Verified on Linux: all 20 tests in the file still pass (skips don't fire here).

### Changed
```
 tests/test_mutate_journal.py | 11 +++++++++++
 tickets/T-3765/ticket.md     | 16 ++++++++++++++--
 2 files changed, 25 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_pytest_session_start_restores_leftover_journal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4323 warning(s), 919 waived
- error-findings: unresolved-attribute@tests/system/test_fleet_status_ground_truth.py
