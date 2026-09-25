---
id: T-draft-5bf0e803
title: 'dropped: approaching/exceeding the 16MB BSON document size limit by embedding'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-929e1bd0
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Document anti-pattern #2. Authority: MongoDB Manual,
"MongoDB Limits and Thresholds": "The maximum BSON document size is 16
mebibytes... To store documents larger than the maximum size, MongoDB
provides the GridFS API" --
https://www.mongodb.com/docs/manual/reference/limits/. Static tier:
"dynamic-only (size is a runtime property; linter can only flag
embedding-without-bound patterns as a proxy, same as #1)" -- the proxy
(unbounded array growth) is ALREADY filed as STORE1's unbounded-array-
growth row (folded into the STORE1xx group's mongo leaves); filing a
SECOND rule for the same proxy shape under a different id would
duplicate STORE105/STORE1xx's array-growth coverage rather than add a
genuinely new static signal.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
