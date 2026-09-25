---
id: T-draft-98159bb1
title: 'dropped: large (multi-MB) values stored in a single Redis key/field'
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

Research file, Key-value anti-pattern #5. Static tier: "dynamic-only
(value size is runtime data; linter can flag `.set()` fed directly from
file-read/serialize-of-large-object as a proxy)" -- the proxy shape
(`.set()` fed from a file-read/serialize call) is the SAME shape
STORE120 already files for the relational blob-in-column case; a
redis-specific twin of that proxy would duplicate coverage rather than
add a new static signal, and the genuinely new information (actual byte
size) is runtime-only.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
