---
id: T-3716
title: adding [vet.allow] silently flips vet from advisory to enforced
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
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
scope:
- src/frob/vet/_hook.py
- src/frob/vet/_allow.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
  new_value: v0.539.0
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
apollo FROBLEMS.md 2026-09-03: adding a [vet.allow] table (the remedy the quarantine message itself prescribes) silently flips vet from advisory to enforced, instantly demanding review of the ENTIRE lockfile (47 errors in apollo's case). The remedy for two packages should not change the mode for twenty. Enforcement should stay scoped to what the allow-list is about, or advisory posture should require an explicit opt-in to flip to enforced.