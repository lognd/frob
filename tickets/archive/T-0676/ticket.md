---
id: T-0676
title: 'registry: fix supply-chain-corpus.md self-inconsistent TOTAL (41 real entries
  vs 39 stated)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0389
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/supply-chain-corpus.md
- docs/design/registry/supply-chain.yaml
- tests/test_registry_reconciliation_supply_chain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_reconciliation_supply_chain.py
  reason: 'covers_scope route 2: the reconciliation pin tests are this ticket''s evidence
    and pin the recounted totals; docs-only scope on a bug-kind ticket cannot satisfy
    D-02 otherwise'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41
- tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted
designated_repro_test: null
acceptance:
- text: Given supply-chain-corpus.md after the fix, when its own TOTAL field is compared
    to registry entry count, then they match
  evidence:
  - tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_declared_total_is_41
  - tests/test_registry_reconciliation_supply_chain.py::TestSupplyChainExhaustiveness::test_audit_reports_exhausted
threat: null
component: null
---
RECONCILIATION.md finding (g): the source doc's own denominator_manifest.entries lists 41 unique ids but its TOTAL field says 39, and the totals_by_class explanation does not account for the raw-list discrepancy. Correct the source doc's TOTAL field to 41 (or explain precisely which 2 entries are non-canonical and should be excluded, if that is the real intent) so the registry and the source doc agree. Depends on T-0389 (supply-chain domain reconciliation) landing so the fix is made against the settled registry entries.