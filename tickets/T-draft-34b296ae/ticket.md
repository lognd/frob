---
id: T-draft-34b296ae
title: Fix DOC011/DOCENUM001 stale doc references and PERF004 loop-sort findings
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
- .claude/hooks/frob-suggest.py
- src/frob/lang/_support.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: T-3358 has an active in-progress lease on this file; DOC011 fix dropped
    from this ticket's scope to avoid lease collision
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
gate:LARGE ER slice: DOC011 (stale T-draft-ad5e921b citation in docs/modules/tickets.md, now T-3360), DOCENUM001 (docs/modules/gates.md rule-catalog enumerate list omitted TDD001/VERSION001/VMOD001), and two PERF004 sort-in-loop findings (.claude/hooks/frob-suggest.py, src/frob/lang/_support.py -- both waived with per-iteration-varies-input reasoning since a hoist is not correct there).