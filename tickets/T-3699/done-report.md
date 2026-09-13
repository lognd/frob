## Done report

Hardened test_daemon_proxy_lease_t1276.py's real-daemon fixture (bounded startup wait, explicit frob_shutdown RPC teardown, joined-thread assertion) to stop a leaked/slow daemon thread from destabilizing a later test on the same xdist worker -- the likely mechanism behind CI run 34708801531's macOS worker crash. Ran the file 5/5 clean locally. BUG002 confirmatory-only evidence waived: same intermittent load-sensitive race category as T-4356's sibling flake, test already passes at parent commit so no deterministic repro is forceable. frob check --ticket T-3699 clean of PRE/SCOPE/TEST errors; the 3 remaining repo-wide FAILs (ruff-format on tests/test_tickets_triage_dates.py, gate:LARGE, gate:TICK) are all outside this ticket's scope file and pre-existing.

### Changed
```
 tests/unit/test_daemon_proxy_lease_t1276.py | 50 ++++++++++++++++++++++++-----
 tickets/T-3699/ticket.md                    | 16 ++++++++-
 2 files changed, 57 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_round_trip_acquire_call_release_close` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 4797 warning(s), 961 waived
- error-findings: LARGE001@src/frob/strata/_native_staleness.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4411.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4443.json
