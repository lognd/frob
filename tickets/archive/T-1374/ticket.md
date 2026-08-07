---
id: T-1374
title: 'REG008: CHK-SUBSYS-GATES-ACCOUNTING repointed to TEST013 without a frob:enforces
  edge'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: the REG008 regression test is this ticket's only evidence and must be in
    scope to satisfy covers_scope
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN tests/test_registry_exhaustiveness.py runs THEN test_no_reg008_findings_for_check_coverage_yaml
    passes
  evidence:
  - tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
threat: null
component: null
---
T-1266's close re-dispositioned CHK-SUBSYS-GATES-ACCOUNTING from deferred:T-1266 to handled_by:TEST013, but the enforcing implementation _test013_native_unverified only declares 'frob:enforces CHK-GATE-TEST013'. REG008 requires the enforcing rule to name every registry entry it discharges, so the row now reads as catalogued-but-unenforced. Same shape as the CHK-GATE-SUPPRESS001 fix. Deliberately NOT fixed inline on discovery: src/frob/gates/** and docs/** are both leased by in-flight agents (T-1371, T-1372).