---
id: T-4208
title: 'land: run the type stage with the project venv''s checker (not PATH), and
  print file:line:message diagnostics on refusal'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
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
Consumer F-328 (T-4135). Land refused three times citing '1/2 NEW ty error(s)' with no line numbers, while the worktree's own venv ty and frob check --only ty both reported clean. Root cause: land's type stage ran the globally-installed ty (older) instead of the project venv's ty (matches gate); the refusal message also never printed a diagnostic. Fix both: pin the same binary the gate uses, and always print file/line/code/message on refusal. Same shape as T-4125 (already done for a different refusal path) recurring here for the type stage specifically. Fixture-testable: YES, consumer-blocking now (land blocker).