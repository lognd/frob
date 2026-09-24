---
id: T-3067
title: 'Curated landing: preserve the 2-7 real work commits per ticket, squash the
  9-21 bookkeeping commits, classify by paths touched'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 8
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
- src/frob/tickets/_land_squash.py
- tests/unit/tickets/test_land_squash.py
- docs/guides/landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/tickets/test_land_squash.py
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/guides/landing.md
  reason: 'curated landing: keep real work commits, squash the rest'
  actor: logan
  at: '2026-09-23'
triage_changes:
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
- field: sprint
  old_value: backlog
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: milestone
  old_value: 1.0.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-24: unblocked by T-3053 -- stale edge: T-3053 is the unrelated CAS/update-ref redesign (kernel decoupling); curated landing does not depend on it (measured 2026-09-24)
