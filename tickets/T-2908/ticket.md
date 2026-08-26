---
id: T-2908
title: 'frob-suggest: three nudge rules misfire and tax every agent call with a retry'
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/frob-suggest.py
  reason: fix three misfiring nudge rules and add must-stay-quiet fixtures
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: fix three misfiring nudge rules and add must-stay-quiet fixtures
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
