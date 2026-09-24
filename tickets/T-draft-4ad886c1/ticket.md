---
id: T-draft-4ad886c1
title: 'frob coord status: queue, quarantine, leases vs states, worktree tiers, stale
  locks'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/_cli_parsers/_coord.py
- src/frob/coord/_status.py
- src/frob/coord/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_coord.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/coord/_status.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/coord/__init__.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord status: one screen for the coordinator, run from the root: land queue depth and order with the landing entry and its pid liveness; quarantine state and age; in-progress tickets vs live leases (orphaned leases, tickets in-progress without a lease); worktrees with their disk use and a tier per the safety rule (auto-removable, recommended, needs a flag); stale .git/index.lock and land.lock holders; the last N land outcomes. First non-land consumer of queue_status() and quarantine_status_marker(). Positive control: a fixture with 2 queued + 1 landing entries and a raised quarantine shows queue=3 and RAISED; cleared quarantine shows clear. Replaces scripts/fleet_status.py and the coordinator's python one-liners.
