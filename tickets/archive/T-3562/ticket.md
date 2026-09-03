---
id: T-3562
title: 'REG008 residue: check-coverage.yaml entry from T-3554 sync missing a required
  field'
state: done
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml fails with a Violation list: T-3554's frob registry audit --sync-gate-rules added an entry to docs/design/registry/check-coverage.yaml missing whatever REG008 requires. Run the test locally, it names the field; fix the yaml entry properly.