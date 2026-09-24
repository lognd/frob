---
id: T-5751
title: Add due date to milestone/sprint-bearing tickets and rank sibling-ordering
  hint to Ticket/TicketSpec
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: T-draft-b2d257c3
  new_value: T-5748
  reason: re-parent to the promoted story id; story draft was promoted after this
    leaf was filed and the child parent field was not rewritten
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add due: date | None to milestone/sprint-bearing tickets and rank: int | None (explicit sibling ordering hint) to Ticket/TicketSpec.

Positive control: frob ticket new --due 2026-12-01 --rank 3 round-trips; a rank collision within one parent is tolerated (ordering hint, not a unique key) and does not raise. State the non-uniqueness explicitly in the doc page.

Doc page: docs/modules/tickets-data-storage.md#data-models

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
