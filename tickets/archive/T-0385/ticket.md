---
id: T-0385
title: 'registry reconciliation: patterns (346 patterns)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
- T-0343
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/vet/
- docs/design/registry/patterns.yaml
- tests/test_registry_reconciliation_patterns.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_patterns.py
  reason: evidence node ids live in this pin-test file; patterns.yaml was already
    fully dispositioned by T-0407/T-0426 so the pin test IS the deliverable
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_is_in_registry_files
- tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_loads_without_error
- tests/test_registry_reconciliation_patterns.py::TestPatternsRegistryFile::test_no_malformed_entries
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_declared_total_is_346
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_patterns.py::TestPatternsExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_patterns.py::TestExhaustivenessGateOverRealPatterns::test_no_patterns_violations
designated_repro_test: null
threat: null
component: null
---
Reconcile docs/design/registry/patterns.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.