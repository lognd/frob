---
id: T-0390
title: 'registry reconciliation: evasion (112 entries)'
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
- docs/design/registry/evasion.yaml
- tests/test_registry_reconciliation_evasion.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_evasion.py
  reason: add pin test file for T-0390 acceptance criterion, per agent-playbook.md
    evidence discipline
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile::test_is_in_registry_files
- tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile::test_loads_without_error
- tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile::test_no_malformed_entries
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_declared_total_is_112
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_evasion.py::TestExhaustivenessGateOverRealEvasion::test_no_evasion_violations
designated_repro_test: null
threat: null
component: null
---
Reconcile docs/design/registry/evasion.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.