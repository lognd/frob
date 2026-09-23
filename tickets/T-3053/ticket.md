---
id: T-3053
title: 'Land H1: the land pipeline is a hand-compensated saga across four stores --
  compose out-of-tree and publish via update-ref CAS'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-4654
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
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
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: parent
  old_value: null
  new_value: T-4654
  reason: 'kernel-decoupling epic T-4651: rederive the frob kernel behind enforced
    module boundaries; this ticket already states the right work for this concern
    and is adopted as a child rather than duplicated'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: backlog
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-02: unblocked by T-3088 -- T-3688: stale block edge -- T-3088 (decomposition child) is done/archived; clearing to resolve TICK004 rot on T-3053
