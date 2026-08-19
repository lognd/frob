---
id: T-2606
title: waiver reasons promising a follow-up ticket should be enforced
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: T-2377 holds live in-progress lease on docs/modules/gates.md; narrowing
    to src file only, will coordinate/re-add doc scope once free
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2598 found a waiver (AFFECT001 on src/frob/app/cycle_runner.py:32) whose reason promised
a follow-up ticket that was never filed -- the only record of owed work lived inside the
comment suppressing the finding that would have surfaced it.

Consider whether WAIVE001 (or a new rule) should require a real ticket id in any waiver
reason that names future/deferred work ("a follow-up ticket will...", "once X clears..."),
so a promised-but-unfiled follow-up cannot hide behind a waiver indefinitely. Investigate
feasibility (a waiver reason is free text; detecting "promises future work" reliably may
need a narrow phrase/pattern check rather than full NLP) before committing to an approach.
