---
id: T-6432
title: 'STORE111: Cartesian product from disconnected `MATCH` patterns (Neo4j)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6439
- T-6414
parent: T-6457
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
scope:
- src/frob/store/_neo4j.py
- tests/fixtures/store/store111-neo4j-disconnected-match/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 782
  new_length: 920
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE111.

Authority: Neo4j's pattern/tuning docs address the mechanism generally
(https://neo4j.com/docs/cypher-manual/current/patterns/reference/); the
research file flags this row as a **gap** -- no standalone verbatim
"Cartesian product" warning was extracted from the fetched pages this
pass, cross-referenced instead from the planner's exhaustive-search
discussion. Blocked by T-STORE-401-GAPS.

Call shapes: `MATCH (a:A), (b:B) RETURN a,b` -- two comma-separated
patterns with no shared variable/relationship between them.

Detection: parse Cypher for multiple comma-separated `MATCH` patterns
with no shared identifier across them.

Positive-control fixture:
`tests/fixtures/store/store111-neo4j-disconnected-match/`.

Relevance gate: neo4j driver import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
