---
id: T-6473
title: 'dropped: S3 key path used as a queryable "schema", listing as the primary
  query path'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6463
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

Research file, Object storage anti-pattern #3. Static tier:
"dynamic-only (requires knowing listing is the PRIMARY query path vs an
occasional operational tool)" -- the key-construction-plus-
`ListObjectsV2(Prefix=...)` shape is structurally identical whether it
is an occasional admin script or the app's main lookup path; only call
FREQUENCY/centrality in the real request flow (a runtime/operational
property) distinguishes the two.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
