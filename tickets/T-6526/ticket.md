---
id: T-6526
title: 'a11y gate: give a11y_findings a real repo root so _locate_statement_page can
  leave test-only status'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
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
- src/frob/webapp/_a11y_statement.py
- src/frob/gates/_a11y_gate.py
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
Follow-up split off T-5454 (done) and surfaced while repointing a stale
WIRE002-flagged WIRE001 waiver on `_locate_statement_page`
(src/frob/webapp/_a11y_statement.py:127).

`_locate_statement_page`'s own docstring documents that it is "not wired
into any production caller (only this module's own tests use it
directly) -- kept as a small, explicit-root building block for a future
ticket that widens the hook contract" because `a11y_findings`'s per-file
gate hook (T-5323 contract) has no reliable repo root to check against
from inside a single-file hook invocation.

Scope: give the a11y gate hook a real repo root (or equivalent) so
`_locate_statement_page` can be called from `a11y_findings`'s production
path instead of staying test-only, then drop its WIRE001 waiver.
