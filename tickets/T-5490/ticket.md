---
id: T-5490
title: WEBSEC317 + T-5141 secret-pattern reuse for WEBSEC316
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_debug_config.py
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
found while working T-5329: WEBSEC310-316 used 7 of the reserved WEBSEC310-317 8-id block; WEBSEC317 (default-creds cross-refs SEC001-003 per ticket body, no distinct check defined) is left unimplemented. Also, WEBSEC316's secret-literal pattern table is a small self-contained copy pending T-5141's own reusable secret-pattern table landing -- fold WEBSEC316 onto that table once it exists.