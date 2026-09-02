---
id: T-3053
title: 'Land H1: the land pipeline is a hand-compensated saga across four stores --
  compose out-of-tree and publish via update-ref CAS'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
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
- field: priority
  old_value: critical
  new_value: high
  reason: 'T-3688: TICK004 rot -- epic''s only decomposed children (T-3088/T-3089)
    are both done, no other child or claimant is actively working it; critical''s
    3d rot threshold does not match its real cadence as a large, not-yet-scoped land-pipeline
    epic. High keeps it visible without falsely alarming every 3 days.'
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-02: unblocked by T-3088 -- T-3688: stale block edge -- T-3088 (decomposition child) is done/archived; clearing to resolve TICK004 rot on T-3053
