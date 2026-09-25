---
id: T-5766
title: 'Reclassify the 39 stories by flavour and the 11 kind: invariant tickets as
  quality-objective stories, then retire kind: invariant'
state: planned
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
- T-5761
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
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
scope_breadth_ack_reason: bulk ledger migration over story and invariant rows only;
  ticket-count-scaled by design
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '8'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: record the E2 scope cut per coordinator instruction
  actor: logan
  at: '2026-09-25'
  old_length: 742
  new_length: 1208
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reclassify the 39 stories: set flavour per E1's output and split any that are really two requirements. Also reclassify the 11 existing kind: invariant tickets (owner decision Q3; NOT 913, the planner miscounted) as tier: story, flavour: quality_objective, each given exactly one child ticket carrying its evidence; then retire kind: invariant from TicketKind.

Positive control: post-edit grep -c '^flavour:' over story rows equals 39 + 11 = 50; zero tickets remain with kind: invariant; TIER002 runs clean against the reclassified set.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).


Scope cut (coordinator-approved 2026-09-24/25): the evidence-split into a child ticket per invariant, and the retirement of TicketKind.invariant from the enum, are deferred to T-draft-4ba74499 ("invariant stories: split evidence into child tickets and retire TicketKind.invariant", parent T-5748, blocked by T-5766, milestone v0.536.0, 5 pts). This leaf (T-5766) does the tier=story/flavour=quality_objective reclassification of all 11 kind:invariant tickets only.