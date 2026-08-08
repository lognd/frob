---
id: T-1539
title: 'PERF012 registry-entry gap: PERF012 detector exists with no CHK-GATE-PERF012
  registry row'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_waive.py
- tickets/T-1539/**
- tests/test_gates.py
- tickets/T-1800/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1539: add missing CHK-GATE-PERF012 row'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/perf/_rules.py
  reason: 'T-1539: PERF012 registry row also needs a frob:enforces directive in perf_rules
    to satisfy REG008'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: src/frob/perf/_rules.py
  reason: 'T-1539: revert - fix belongs in _waive.py''s _KNOWN_GATE_RULES, not a new
    frob:enforces edge (avoids closure blowup)'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1539: PERF012 missing from _KNOWN_GATE_RULES (why REG010 never caught
    the gap); tickets dir needed for own Done report/ledger files'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1539/**
  reason: 'T-1539: PERF012 missing from _KNOWN_GATE_RULES (why REG010 never caught
    the gap); tickets dir needed for own Done report/ledger files'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1539: TestKnownGateRuleIds verifies the _KNOWN_GATE_RULES literal this
    ticket edits'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1800/**
  reason: 'T-1539: filing this follow-up ticket during T-1539''s own work created
    this file in the touched set'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
designated_repro_test: null
threat: null
component: null
---
Refiled: original draft T-1539 (filed during T-1225's perf-detector work) died in the t-1350 ledger corruption spans. PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225.