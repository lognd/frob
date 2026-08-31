---
id: T-3552
title: 'macOS: identity-less-environment test still resolves the runner OS identity,
  not just git config'
state: in-progress
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record macOS-only BUG002 waiver
  actor: logan
  at: '2026-08-31'
  old_length: 0
  new_length: 361
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive BUG002 reason="macOS-only defect verified from CI run 33361224273 (assert Anka <runner...local> == frob-bot <...>): the OS-account gecos-identity fallback this fixes only fires on a runner whose local account has a real gecos full name (macOS); this Linux dev box account has none, so the pre-fix state already passed here and cannot fail-then-pass."