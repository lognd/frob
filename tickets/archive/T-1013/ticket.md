---
id: T-1013
title: T-0998 gate smoke
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/callgraph.py
- docs/modules/graph.md
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: widen for smoke test
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_graph.py
  reason: widen for smoke test
  actor: logan
  at: '2026-07-27'
designated_repro_test: null
threat: null
component: null
---
## Drop reason
- 2026-07-27: smoke test throwaway, real production SCOPE002 firing proof captured for T-0998 Done report