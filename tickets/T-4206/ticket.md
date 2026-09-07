---
id: T-4206
title: land/scope refusal messages must state why an untouched file is attributed
  to this ticket
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
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
Consumer F-339 second half (T-4135): a land was refused on a doc-pointer citation of a file the land never touched, with no statement of why that file was attributed. Same diagnostic gap as T-4125 (now done) recurring in a different code path -- file fresh rather than reopen a done ticket. The first half of F-339 (paths under the agent-worktree scratch directory should never be consulted by the doc-pointer rule either way) is the same class already tracked as T-4180 (nested worktree paths leaking into gate inputs) -- attach that evidence there instead of a new leaf. Fixture-testable: YES.