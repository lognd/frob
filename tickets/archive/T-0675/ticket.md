---
id: T-0675
title: 'registry: resolve compliance/secrets/pii leaf-granularity gap (599+56+44 leaf
  items)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0388
- T-0386
- T-0387
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/compliance-corpus.md
- docs/design/secrets-pii-corpus.md
- docs/design/registry/**
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only registry ticket; CLI-dispatch integration test is the bound evidence
    (T-0167 precedent), scope-added for covers_scope (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: Given the decision made, when RECONCILIATION.md is reread, then finding (f)
    is marked resolved with either the leaf-level registry built or a written granularity-freeze
    rationale
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
RECONCILIATION.md finding (f): compliance-corpus.md/secrets-pii-corpus.md are unit-granular (27+3+7 = 37 entries) but their own TOTAL_LEAF_CONTROLS_ENUMERATED fields imply 599+56+44 = 699 individually addressable leaf items that were never actually enumerated row-by-row in the source docs. Make an explicit decision: either (a) expand the source docs to real leaf-level enumeration with stable ids and rebuild the registry at that granularity, or (b) formally freeze at unit granularity with a written rationale recorded in registry/README.md and RECONCILIATION.md, closing the gap as a documented decision rather than an open question. Depends on the three unit-granularity reconciliation tickets having landed.