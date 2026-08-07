---
id: T-0017
title: Pair-level (consumer x provider) integration test obligations for TEST003
state: dropped
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
TEST003 alpha semantics treat every src/<pkg> directory with a public symbol as an interface owing min_integration edges (an honest over-approximation, per docs/modules/gates.md's Phase 4 notes). Deferred: derive real consumer x provider pairs once frob.graph gains cross-file import edges, and require min_integration per pair rather than per provider.

Delivered under T-0042.