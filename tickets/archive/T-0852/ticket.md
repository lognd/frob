---
id: T-0852
title: 'gate: TEST016 missing CHK-GATE-TEST016 registry entry (REG010, pre-existing)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/check-coverage.yaml
- tests/test_check_coverage_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_check_coverage_registry.py
  reason: evidence test file for the registry entry fix; covers_scope needs a code
    path for a bug-kind ticket (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-0851: TEST016 is a live gate rule id in
frob.gates._KNOWN_GATE_RULES (T-0755) but has no CHK-GATE-TEST016 entry
in docs/design/registry/check-coverage.yaml -- REG010 (WARN) fires for
it, and tests/test_check_coverage_registry.py's
TestCheckCoverageRegistryFile.test_gate_rule_entries_match_live_known_rules
and TestExhaustivenessGateOverRealCheckCoverage.test_no_check_coverage_violations
both fail on main because of it (pre-existing, confirmed unrelated to
T-0851's own FMT001 addition, which is correctly registered).

Fix: add a CHK-GATE-TEST016 entry (disposition handled_by:TEST016) to
check-coverage.yaml and bump gate_rule_total, or run
`frob registry audit --sync-gate-rules` to file it mechanically.