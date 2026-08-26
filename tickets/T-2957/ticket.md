---
id: T-2957
title: 'frob-dup: burn the family to zero and promote WARN to ERROR (restores T-2378''s
  original commitment)'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
blocked_by:
- T-2955
- T-2956
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-0969
  reason: T-2378 was marked done after amending its acceptance criteria from burn-to-zero-and-promote
    down to the single pair it fixed (1 of 557 findings); T-2957 restores the original
    commitment and is gated on the two triage children
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
