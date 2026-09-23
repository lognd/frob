---
id: T-5361
title: 'LAUNCH checklist: advisory-only convention items'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5360
- T-5304
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_launch_checklist.py
- tests/fixtures/webapp/launch1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Team photo, case studies, FAQ count, thank-you page, sticky mobile CTA, response-time promise, analytics presence -- per the owner directive these NEVER error. Use WEBSUB-4's new advisory Severity tier (not a never-fail flag on warn). File-existence/text-search checks only, no gate-blocking output.