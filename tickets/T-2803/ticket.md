---
id: T-2803
title: 'Document and enforce: drop --absorbed-by for already-resolved findings, fail
  only for genuine blockers'
state: queued
kind: docs
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2796 (backlog reproduction measurement).

Agents were instructed to run `frob ticket fail` when a ticket's stated
defect turned out to already be resolved by landed work. `fail` REQUEUES
the ticket, so this verdict returns it to the pool for the next agent to
rediscover and re-measure at full cost (one instance sat requeued this
way until dropped by hand: T-2692).

The correct split, which needs to be documented and enforced:
- already resolved by landed work -> `frob ticket drop --absorbed-by <id>`
  (terminal, names the survivor, preserves the measurement)
- blocker still genuinely real     -> `frob ticket fail` (requeue is right)

Document this distinction in docs/guides/agent-playbook.md (near section
5, evidence recording, or a new subsection in section 0) since that page
is the canonical home this repo already uses for exactly this class of
process lesson, and every worktree agent reads it per-ticket. Consider
also a one-line addition to `frob ticket fail --help` noting it requeues
and is the wrong verb for "already resolved".
