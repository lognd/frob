## Done report

T-1266's close re-dispositioned CHK-SUBSYS-GATES-ACCOUNTING from
`deferred:T-1266` to `handled_by:TEST013`, which is the correct
disposition -- the real ctest collector plus TEST013's disclosure do
discharge that row. But REG008 requires the enforcing implementation to
NAME every registry entry it discharges, and `_test013_native_unverified`
only declared `frob:enforces CHK-GATE-TEST013`. Without the second edge
the row read as catalogued-but-unenforced: exactly the failure mode the
registry gate exists to catch, and the same shape as the earlier
CHK-GATE-SUPPRESS001 fix.

Added the missing `frob:enforces CHK-SUBSYS-GATES-ACCOUNTING` edge. This
was the last of the four failures that made `make coverage` red, and
therefore the last thing blocking a trustworthy coverage stamp -- with
T-1363's fix in place, a single failing test stops the stamp from being
written at all.

### Changed
(no changed files detected)

### Evidence
- `tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 4 error(s), 2051 warning(s), 695 waived
- error-findings: E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1374
