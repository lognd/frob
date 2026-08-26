---
id: T-2928
title: 'WIRE001 and REF002 both MISS provably dead symbols: measured 1-of-3 detector
  hit rate on a controlled deletion'
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- src/frob/gates/_refs.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_wire.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_refs.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
