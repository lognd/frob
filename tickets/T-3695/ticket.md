---
id: T-3695
title: 'frob-timeout-guard: exempt --help/-h/--version/--dry-run'
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-timeout-guard.py
- tests/test_hook_frob_timeout_guard.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/claude-hooks.md
  reason: close doc scope-closure gap flagged at ticket creation
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob-timeout-guard.py forces a large tool timeout on long frob verbs with no exemption for --help/-h/--version/--dry-run. uv run frob ticket new --help gets blocked though it cannot stall. Exempt invocations whose args contain --help/-h/--version/--dry-run (read-only and fast). Regression test: uv run frob ticket new --help and frob check --help pass without a timeout wrapper; a real frob ticket land (no such flag) still requires the timeout.