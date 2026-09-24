---
id: T-5776
title: 'Audit the 42 epics: close all-children-done ones via TIER003, record an outcome
  check or a dropped reason for the rest'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5780
- T-draft-76f89687
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
- tickets/T-*/ticket.md
scope_breadth_ack: true
scope_breadth_ack_reason: bulk ledger audit over epic rows only; ticket-count-scaled
  by design
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '8'
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
Audit the 42 epics: close the all-children-done ones via TIER003, and for the rest record an outcome check or file a dropped reason.

Positive control: post-audit, zero epics are both all-children-done and still open; every remaining open epic has either an outcome-check field or a dropped child recording why not.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
