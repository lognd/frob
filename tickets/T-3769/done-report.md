## Done report

Moved the win32 platform-skip check in test_windows_backend_round_trips ahead of 'import fcntl', which does not exist on real Windows and crashed the test with ModuleNotFoundError before the intended skip ever ran. Evidence: tests/ticket_land_suite/test_land_lock.py::TestLandLockPlatformBackends::test_windows_backend_round_trips. Confirmed via winrun on the Windows mirror (Python 3.12.10): test now SKIPPED cleanly (exitstatus=0) instead of crashing. Filed: none. Gates: frob check --ticket T-3769 pending.

### Changed
```
 tests/ticket_land_suite/test_land_lock.py | 12 +++++++++---
 tickets/T-3769/ticket.md                  |  4 +++-
 2 files changed, 12 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/ticket_land_suite/test_land_lock.py::TestLandLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
