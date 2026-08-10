---
id: T-2029
title: Retire the T-1964 AFFECT001 waiver in fix_engine_sync now that the gates.md
  WAIVE004 writeup has landed
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1964 landed the deferred docs/modules/gates.md WAIVE004 wiring writeup. src/frob/gates/_fix_engine_sync.py:953 still carries a frob:waive AFFECT001 comment with follow_up="T-1964" from when the doc write was blocked by T-1958's lease. Now that the doc exists, ack the AFFECT001 finding on that function normally and remove the waiver (or re-point follow_up to this ticket until acked).