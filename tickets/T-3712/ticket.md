---
id: T-3712
title: make T-2691 DOC006 regression test self-contained
state: in-progress
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
- tests/unit/test_ticket_2691_doc006.py
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
CI blocker on ubuntu/macos (run 33711053377): test_real_ticket_file_not_flagged reads live tickets/T-2691/ticket.md which was archived to tickets/archive/T-2691/ticket.md this session. Replace live-file dependency with a self-contained fixture reproducing T-2691's original content shape.