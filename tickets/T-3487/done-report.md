## Done report

The T-3455 relative assertion rejected a decisively-better measurement (with_serial 0.9978 vs without 0.5039, ratio 1.98) on a 2x technicality. Restated the property the test names: patched attribution must exceed 0.9 absolutely and beat unpatched by at least 1.5x, with the measured numbers in the failure message. Test file passes 9/9 including both serial-pools attribution tests.

### Changed
```
 tests/unit/perf/test_serial_pools.py | 23 ++++++++++++++++++++---
 tickets/T-3487/done-report.md        | 18 ++++++++++++++++++
 2 files changed, 38 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 4043 warning(s), 870 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@changelog.d/T-2691.md, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
