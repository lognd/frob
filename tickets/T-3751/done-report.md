## Done report

First verified fixes of the win32 test-portability drain (T-3076). Both test_coverage_wait_shared and test_serve_socket carry a test_windows_backend_round_trips that exercises the msvcrt (Windows) lock backend ON POSIX by standing a fake msvcrt on top of real fcntl.flock. On real Windows fcntl does not exist (ModuleNotFoundError) and the actual msvcrt backend runs instead, so the POSIX simulation is inapplicable -> skipif(sys.platform=='win32') with a reason. Verified on a live Windows run via the local C: mirror: both now SKIP (exit 0) instead of erroring. BUG002 waived: Windows-only defect, no Linux repro (fcntl exists there). DEPR006 pre-existing/out-of-scope.

### Changed
```
 tests/test_coverage_wait_shared.py | 6 ++++++
 tests/test_serve_socket.py         | 6 ++++++
 tickets/T-3751/ticket.md           | 7 ++++++-
 3 files changed, 18 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4335 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
