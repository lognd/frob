## Done report

win32 CI fails these tests because os.nice does not exist on Windows -- genuinely POSIX-only. Added skipif(sys.platform==win32) at method level on both. Verified on Linux: all 36 tests in the file still pass (skips don't fire here).

### Changed
```
 tests/unit/verify/test_worker.py | 11 +++++++++++
 tickets/T-3764/ticket.md         | 16 ++++++++++++++--
 2 files changed, 25 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_applies_nice_and_ionice_exactly_once` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_failed_nice_call_never_raises` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4323 warning(s), 920 waived
- error-findings: unresolved-attribute@tests/system/test_fleet_status_ground_truth.py
