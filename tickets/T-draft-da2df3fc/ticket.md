---
id: T-draft-da2df3fc
title: Automatic per-session token mining for tickets (T-5132 amendment follow-up)
state: queued
kind: feature
origin: human
created: '2026-09-22'
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
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_setters.py
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
found while working T-5132: the owner's amendment asked for automatic token-spend recording (session id captured on the lease at start, transcript jsonl summed at close/land) alongside the manual frob ticket tokens path that DID ship this ticket. Left out of T-5132's scope for time -- only the manual setter shipped.