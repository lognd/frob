---
id: T-5819
title: ticket promote leaves dangling parent/blocked_by references and drops evidence
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
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
- src/frob/tickets/_draft_finalize.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_draft_finalize.py
  reason: fix land-path draft promotion leaving dangling parent/blocked_by references
    on already-landed main-ledger tickets
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket promote T-draft-x` renames the ticket but leaves every
OTHER ticket's `parent:` and `blocked_by:` references to the draft id
dangling (measured 2026-09-24 while filing the coord tree: promoted
leaves lost their parent wiring and blockers; T-draft-342a3548 -> T-5518
lost its evidence and done report on promotion as well). Fix: promotion
rewrites all inbound references across the ledger in the same commit and
carries the ticket directory's evidence/done-report content byte-for-
byte; positive control: a parent with two draft children, promote one,
the sibling's blocked_by and the parent's child list must name the new
id; evidence ids must survive.
