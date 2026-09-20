## Done report

land_process_rows own ps-based scan had NO cwd/repo filter, so it could match a frob ticket land in a completely different repository or its own ancestor process tree (this script running as a diagnostic child of a live land). Mirrored the ALREADY-FIXED T-3885 shape (frob.tickets._leases._process_ancestor_pids/_scan_for_live_land_process) rather than reinventing a predicate: _proc_ppid/_process_ancestor_pids duplicated in plain form (this scripts documented no-frob-import contract), _pid_cwd added for the repo-scope check, both filters delegated to a new _land_row_is_out_of_scope helper to keep land_process_rows under ARCH001 (waived: pure doc-density growth, no new branching). Two new regression tests confirmed RED against the unfixed code (committed separately, then the fix) before being confirmed GREEN; BUG002 check-repro against that test-only commit passed as a genuine repro, no waiver needed.

### Changed
```
 docs/guides/coordinator-scripts.md              |  19 ++++
 scripts/fleet_status.py                         | 131 +++++++++++++++++++++++-
 tests/unit/coordinator_suite/test_fleet_land.py |  72 +++++++++++++
 tickets/T-4377/ticket.md                        |  17 +++
 4 files changed, 238 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/coordinator_suite/test_fleet_land.py::TestLandProcessRows::test_a_land_in_a_different_repo_is_not_counted` (pytest node id, verified passing when recorded)
- `tests/unit/coordinator_suite/test_fleet_land.py::TestLandProcessRows::test_own_ancestor_process_is_not_counted_as_a_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4872 warning(s), 959 waived
- error-findings: none (measured, zero errors)
