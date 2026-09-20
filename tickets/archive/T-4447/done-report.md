## Done report

Added Violation.severity_pinned (src/frob/findings.py), set it in _platform_skip_violation (COV003) and _test002_platform_skipped (TEST002) in src/frob/gates/__init__.py, and made _apply_severity_overrides (src/frob/gates/_waive.py) skip pinned violations alongside UNRESOLVED. Measured on the Windows mirror (winrun, worktree checkout with the fix applied): frob check --only coverage --only test --json now reports all 56 COV003 + 2 TEST002 stackdump-module platform-skip findings at their intended severity (warning/info), 0 at error -- versus the 56 COV003 + 2 TEST002 errors T-4444 recorded before this fix. Bound 5 new unit tests as evidence (T-4447): tests/unit/test_findings_severity_pinned.py (Violation default, both verdict builders pin correctly) and tests/gates_suite/test_severity_overrides_pin.py (override leaves a pinned WARN alone, still promotes an unpinned one). frob check --ticket T-4447 is clean of anything in T-4447's scope (remaining 3 errors are pre-existing/unrelated: LARGE001 on src/frob/strata/_native_staleness.py, and TICK010 lease-reference findings for T-4411/T-4412's worktrees). Scope was widened per coordinator instruction to add src/frob/findings.py, src/frob/gates/__init__.py, tests/unit/test_findings*.py, and docs/modules/gates.md (needed to close AFFECT001 on the new Violation field).

### Changed
```
 docs/modules/gates.md                            | 11 +++-
 src/frob/findings.py                             | 16 ++++++
 src/frob/gates/__init__.py                       | 16 +++++-
 src/frob/gates/_waive.py                         | 15 +++++-
 tests/gates_suite/test_severity_overrides_pin.py | 60 +++++++++++++++++++++
 tests/unit/test_findings_severity_pinned.py      | 67 ++++++++++++++++++++++++
 tickets/T-4447/ticket.md                         | 41 +++++++++++++++
 7 files changed, 221 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_findings_severity_pinned.py::test_violation_defaults_severity_pinned_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_findings_severity_pinned.py::test_platform_skip_violation_is_pinned` (pytest node id, verified passing when recorded)
- `tests/unit/test_findings_severity_pinned.py::test_test002_platform_skipped_is_pinned` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_severity_overrides_pin.py::test_override_never_escalates_pinned_warn` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_severity_overrides_pin.py::test_override_still_escalates_unpinned_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 4937 warning(s), 960 waived
- error-findings: LARGE001@src/frob/strata/_native_staleness.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4411.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4412.json
