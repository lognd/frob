---
id: T-0674
title: 'registry: adjudicate CWE Top-25 vs cwe-1000-registry.md classification tension
  (6 CWEs)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0384
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- docs/design/security-corpus.md
- docs/design/cwe-1000-registry.md
- tests/test_registry_reconciliation_weaknesses.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_weaknesses.py
  reason: 'covers_scope route 2 (T-0676 land lesson): the reconciliation pin test
    is the evidence and pins the adjudicated registry state; docs-only scope on a
    security-kind ticket cannot satisfy D-02 otherwise'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations
designated_repro_test: null
acceptance:
- text: Given the 6 tension CWEs, when reviewed, then each has one final ruling recorded
    in weaknesses.yaml with a cross_ref to security-corpus.md's Top-25 entry
  evidence:
  - tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations
threat: null
component: null
---
RECONCILIATION.md finding (e): CWE-120/121/122/200/284/770 are treated as directly checkable by security-corpus.md's Top-25 tags but reclassified duplicate-of/out-of-scope by cwe-1000-registry.md's stricter rule-based classifier. Make one ruling per CWE, update whichever source doc/registry entry is wrong, and record cross_refs (security-corpus:cwe-top25-2025) once resolved. Depends on T-0384 (weaknesses reconciliation) landing first since that is where the CWE disposition truth lives.