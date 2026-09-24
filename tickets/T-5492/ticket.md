---
id: T-5492
title: 'doc: document ledger-only CAS retry apply-conflict fix (T-5491)'
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 2
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
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5491: docs/modules/tickets-landing.md's T-4572 section describes the fast path as a fixed 5-attempt bound that gives up on any rebase failure; T-5491 changed this to distinguish apply-conflict-retryable from non-ledger-only, with a drift-proportional bound -- update the doc section accordingly once T-5518's lease on this file clears