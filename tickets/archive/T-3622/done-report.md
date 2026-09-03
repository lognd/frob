## Done report

Split _land_flock_probe (fd-open helper _open_land_lock_fd_for_probe) and
_live_pids_with_cwd (platform dispatch to _live_pids_with_cwd_linux/
_live_pids_with_cwd_darwin, with lsof spawn split into _run_lsof_cwd_query
and line-parsing split into _parse_lsof_pid_lines) along their concern
boundaries. Behavior identical -- pure decomposition.

Evidence: existing test files re-run against the decomposed code (moved/
covering tests, per split precedent T-3586/096c8916) --
tests/test_tickets_leases.py, tests/test_ticket_leases.py,
tests/test_ticket_leases_cross_worktree.py (211 passed, 0 failed).

Filed: none.

Gates: frob check --ticket T-3622 shows zero ARCH103 findings on
src/frob/tickets/_leases.py (both --only arch and full --ticket runs).
Remaining scoped errors (23) are pre-existing/out-of-scope: ARCH102 on
_lock.py/_land_squash.py and LARGE001 on root-write-guard.py/_mayraise.py
are later tickets in this same series; COV/INV/DEPR/OPAQUE/PII/REL/TEST/
WAIVE items are in unrelated files.

### Changed
```
 src/frob/tickets/_leases.py   | 181 +++++++++++++++++++++++++++++-------------
 tickets/T-3622/done-report.md |  35 ++++++++
 tickets/T-3622/ticket.md      |   5 +-
 3 files changed, 163 insertions(+), 58 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_allows_when_no_lock_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_belt_and_braces_process_scan_without_the_lock_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 15 error(s), 4176 warning(s), 903 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, INV001@invariants/INV-011.md, INV001@invariants/INV-013.md, INV001@invariants/INV-041.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PII012@tests/gates_suite/test_compliance.py, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
