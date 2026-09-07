---
id: T-4198
title: frob ticket start's behind-main warning should name the ticket's declared base
  branch, not hardcode main
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: low
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner
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
Consumer F-319 (T-4135). An agent on a worktree cut from a non-main base branch followed start's 'merge main' suggestion, pulled in main-only files, and produced spurious SCOPE001s under --base <declared-base>. Name the ticket's declared base (or the branch the worktree was cut from). Fixture-testable: YES.