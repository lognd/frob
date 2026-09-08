---
id: T-4197
title: 'DSL001: a malformed or free-text frob:tests/frob:waive directive must raise
  a parse-time finding, not silently no-op'
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: F-318/F-333's own precedent (T-4260) concluded a malformed frob:tests/frob:waive
    directive is wrong the moment it is written and belongs at parse time, in the
    directive scanner (frob.graph.dsl), not inside the gate that later consumes the
    resulting edge; the declared src/frob/gates scope covers only the gate-side symptom
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consolidates F-318 (a free-text symref in frob:tests parsed silently, TEST002 counts went to zero) and F-333 (a multi-line frob:waive continuation line missing the # prefix silently failed to attach) -- same silent-zero-in-our-own-DSL mechanism, one leaf. Fixture-testable: YES, consumer-blocking now.