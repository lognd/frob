---
id: T-5283
title: frob.app._config_external missing T-5132 CLI field allowlist entries (points/tokens/unsized-ack
  silently dropped)
state: dropped
kind: bug
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
- src/frob/app/_config_external.py
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
found while working T-draft-ac05cce9 (the T-5132 LEDGER_VERB_STRATEGY fix): _config_external.py's from_external allowlist never got ticket_points, ticket_points_value, ticket_unsized_ack, ticket_tokens_in, ticket_tokens_out, ticket_tokens_cache_read added -- every one of those CLI flags is silently dropped to its AppConfig default on a real frob invocation (only visible via direct AppConfig construction in tests, e.g. --points on new, --unsized-ack on start, and frob ticket points/tokens's own value are all affected). Blocked from fixing directly in T-draft-ac05cce9: src/frob/app/_config_external.py is leased by T-4702.

## Drop reason
- 2026-09-22: allowlist entries landed inside T-4702 (197238c35e) (absorbed by T-4702)
