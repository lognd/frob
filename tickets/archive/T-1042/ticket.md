---
id: T-1042
title: 'REG008 remainder: enforces edges for compliance/system-design/check-coverage
  registries (134)'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/design/registry/compliance.yaml
- docs/design/registry/system-design.yaml
- docs/design/registry/check-coverage.yaml
- src/frob/strata/
- src/frob/gates/
- tests/test_registry_exhaustiveness.py
- src/frob/strata/_process_bounds.py
- src/frob/strata/_supply_chain_boot.py
- src/frob/perf/_loop_effects.py
- src/frob/perf/_ratchet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'T-1020 follow-up: add frob:enforces edges + real-repo regression tests
    for system-design.yaml''s SDC-13 REG008 remainder'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_process_bounds.py
  reason: 'T-1020 follow-up: add frob:enforces edges + real-repo regression tests
    for system-design.yaml''s SDC-13 REG008 remainder'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/strata/_supply_chain_boot.py
  reason: 'T-1020 follow-up: add frob:enforces edges + real-repo regression tests
    for system-design.yaml''s SDC-13 REG008 remainder'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/perf/_loop_effects.py
  reason: 'T-1020 follow-up: REG008 CHK-GATE-PERF008/PERF009 enforces edges'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/perf/_ratchet.py
  reason: 'T-1020 follow-up: REG008 CHK-GATE-PERF008/PERF009 enforces edges'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_registry_exhaustiveness.py::TestSystemDesignReg008BurnDown::test_no_reg008_findings_for_system_design_yaml
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
- tests/test_registry_exhaustiveness.py::TestComplianceReg008BurnDown::test_no_reg008_findings_for_compliance_yaml
designated_repro_test: null
threat: null
component: null
---
Follow-up to T-1020: the REG008 remainder measured while working T-1020 (out of that ticket's declared scope). Verify each handled_by:<RULE> attribution against the real enforcing implementation before adding a frob:enforces <ENTRY-ID> edge; flip/downgrade dishonest ones and count them. Real-repo-scan regression test per registry file. Goal: REG008 to zero repo-wide. Coordination note: T-1019 is concurrently rewriting REG011 disposition reasons in weaknesses/patterns/compliance yamls -- different keys, same compliance.yaml file; do the compliance.yaml batch LAST, re-merge main right before it, resolve any conflict keep-both.