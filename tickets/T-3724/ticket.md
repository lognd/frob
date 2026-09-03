---
id: T-3724
title: DOC006 scans free-text scope-change reason strings for pointer syntax
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow scope to the single file the DOC006 reason-field exemption fix touches
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/gates/_docptr.py
  reason: narrow scope to the single file the DOC006 reason-field exemption fix touches
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: a scope-change REASON string (free text, written via the sanctioned frob ticket scope command) mentioning a future config key tripped DOC006 in tickets/T-0016/ticket.md -- frob's own generated ledger failed frob's own gate, and the only fix was a hand-edit the hand-edit hook warns against. Reason strings should be exempt from pointer resolution (or the scope command should warn at write time).