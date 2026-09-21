---
id: T-5252
title: Capstone e2e for the default land queue (order, hygiene, clean refusal, residue
  ticket) and the playbook rewrite that deletes the coordinator runner recipe
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-draft-5d1b6c22
- T-5253
- T-5255
- T-5251
- T-5248
- T-5256
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/ticket_land_suite/**
- docs/guides/agent-playbook.md
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-landing.md
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
Leaf G of T-5106 (~2 pts). Capstone e2e and playbook. Blocked by A B C1 C2 C3 D E.
- tests/ticket_land_suite e2e: a temp repo with three worktrees enqueued out of blocked_by order, one carrying an unpromoted draft, one behind the target branch with a CHANGELOG conflict, one with a planted post-finalize refusal, a raised quarantine from a prior sweep; assert dependency-ordered LAND-PROOFs, clean worktree after the refusal, one residue ticket, queue and status output.
- docs/guides/agent-playbook.md and docs/modules/tickets-landing.md describe the default path in one paragraph each; the coordinator-scripts guide's runner recipe is deleted (T-5106's five scripts are the deleted denominator, count them in the done-report).
