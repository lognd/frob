---
id: T-0391
title: 'registry reconciliation: arch-checks (311 entries)'
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
- src/frob/gates/
- docs/design/registry/arch-checks.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
- tests/test_registry_exhaustiveness.py::TestDisposition::test_out_of_scope_no_reason_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails
designated_repro_test: null
threat: null
component: null
---
Reconcile docs/design/registry/arch-checks.yaml against actual enforcement: every catalogued entry must map to (i) an enforced check, (ii) a documented out-of-scope entry with a verified caught_by (T-0381/T-0382), or (iii) an explicit deferred ticket. Resolve RECONCILIATION.md's undispositioned entries for this registry. Add an EXHAUSTIVENESS meta-test for this registry: catalogued count == enforced+excused+deferred count, so a future gap fails the build. Acceptance: exhaustiveness meta-test passes and is wired into frob check.