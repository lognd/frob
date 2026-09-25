---
id: T-draft-5b5d6cd6
title: 'dropped: single `WITH RECURSIVE` / graph-traversal-by-CTE call with runtime-unbounded
  depth parameter'
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
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 610
  new_length: 748
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Research file, Relational anti-pattern #7 / Graph anti-pattern #5.
Static tier: "dynamic-only (need to see it's called in a loop / with
unbounded depth param)" -- a SINGLE call site with a depth parameter
whose bound is a runtime value cannot be distinguished from a safely
bounded call without knowing what value flows into that parameter at
runtime. Distinct from STORE121 (the CALL-IN-A-LOOP shape, which IS
static and IS filed) -- this dropped ticket is specifically the
single-call, data-dependent-depth case.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
