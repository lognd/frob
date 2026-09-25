---
id: T-6447
title: 'STORE305: search index written as the sole source of truth (no canonical-store
  writer for the same entity)'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6456
- T-6414
parent: T-6508
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
- src/frob/store/_strata_mismatch.py
- tests/fixtures/store/store305-search-as-source-of-truth/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1513
  new_length: 1651
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Rule id: STORE305 (research file section 5, Search anti-pattern #4 --
the "plus the search-as-source-of-truth row" the epic's Story 3
description names explicitly, distinct from the four section-8
cross-cutting rows STORE301-304 cover).

Authority: not a single vendor quote sourced in the research pass; well
established as a documented operational risk in Elastic's own
reindexing and snapshot/restore guidance (not independently fetched this
pass). Research file flags this row **gap**. Blocked by
T-STORE-401-GAPS.

Code shape: app write path that only calls `es.index(...)`/
`es.update(...)` with no corresponding write to a relational/document
store for the same entity; TS/JS: same shape (`client.index(...)`
only).

Detection: this is the one STORE30x rule that genuinely needs strata
rather than a pure code-shape check -- "is there any other writer for
this entity" is answered by strata's own binding graph (does any OTHER
`store` node's `code=` binding also write this entity kind), not by a
whole-codebase data-flow analysis a lexical scanner could fake. If no
second writer binding exists anywhere in the strata graph for the same
entity kind, STORE305 fires.

Positive-control fixture:
`tests/fixtures/store/store305-search-as-source-of-truth/` (a `.strata`
fixture with exactly one `store` node, `engine elasticsearch`, and no
sibling store for the same entity).

Relevance gate: strata `store` node declared with `engine` resolving to
`search` paradigm, and elasticsearch client import detected.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
