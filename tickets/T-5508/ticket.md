---
id: T-5508
title: WEBSEC403 full-strength server-route cross-reference
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
- src/frob/webapp/_websec_authz_routes.py
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
found while working T-5357: WEBSEC403 currently checks only that a React Router admin-path <Route> is wrapped in a guard component, a JSX-local text-regex proxy. The ticket body's full corpus item is a React router-guard AST cross-referenced against the server's own route table (built from the same WEBSEC402 admin-route detection) to confirm the client guard has a matching server-side enforcement. Implement the cross-reference.