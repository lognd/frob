---
id: T-4598
title: 'shared registry files (design/frob.strata, docs/design/registry/capability-via-ratchet.lock.json,
  docs/modules/gates.md rule table, frob.toml severity zone) must be append-shared,
  not whole-file leases: one in-progress ticket holding them blocks every sibling
  land with CrossTicketLeakage and every sibling scope --add with ScopeLeaseConflict'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-4659
parent: T-4653
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
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
- field: parent
  old_value: null
  new_value: T-4653
  reason: 'kernel-decoupling epic T-4651: rederive the frob kernel behind enforced
    module boundaries; this ticket already states the right work for this concern
    and is adopted as a child rather than duplicated'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
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
