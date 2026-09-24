---
id: T-5496
title: WEBSEC217 reserved id follow-up (JWT/OAuth family)
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
worktree: null
branch: null
scope:
- src/frob/webapp/_websec_tokens.py
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
found while working T-5352: WEBSEC209-216 used 8 of the reserved WEBSEC209-217 9-id block; WEBSEC217 has no distinct check defined in the ticket body (secrets-committed is SEC001-003's job) and is left unimplemented -- decide and implement, or formally retire the id.