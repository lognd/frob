---
id: T-0384
title: 'registry reconciliation: weaknesses (944 CWEs)'
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
- src/frob/strata/
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_weaknesses.py
  reason: evidence lives in the pin test
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_is_in_registry_files
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_loads_without_error
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile::test_no_malformed_entries
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_declared_cwe_total_is_944
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_audit_reports_exhausted
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations
designated_repro_test: null
threat: null
component: null
---
Reconcile docs/design/registry/weaknesses.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.