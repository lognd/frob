---
id: T-3625
title: 'frob ticket land: TDD001 pre-land check has no per-land time budget, blocks
  landing large diffs'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_tdd_order.py
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
Found while landing T-3586 (a large, legitimate refactor: 592 files
changed by frob refactor split/move's own repo-wide reference rewrite,
splitting tests/test_gates.py into 14 modules).

`frob ticket land`'s TDD001 pre-land check (src/frob/tickets/_land.py,
`_tdd_order_scoped_edges` / the WARN-only wiring around it, T-3057)
spawns `tdd_order_violations` against every touched `frob:tests` edge
in the diff. MEASURED against this land, repeatedly, at both high
(load avg 7.6) and low (load avg 2.8) host contention: only 1-3 edges
get checked (and logged) in a full 595-second foreground window before
the process has to be killed -- roughly 200-300 seconds PER EDGE,
consistently, regardless of host load. The repeated slow edges are
both against `src/frob/gates/__init__.py`, a file with an unusually
long commit history in this repo; `tdd_order_violations`'s own
docstring already documents that this check "spawns several git
subprocesses per edge" (T-3009's own oldest-first history walk) and
that "an unscoped repo-wide pass measured well over an hour" -- but the
DIFF-SCOPED version, meant to be the fast path, still costs enough per
edge (when the edge's target file carries a large history) that a diff
touching hundreds of edges against a few such files cannot complete
inside any practical foreground land-command budget.

Made 16 consecutive `frob ticket land` attempts (595s foreground cap
each, per this repo's own timeout-guard convention) with zero progress
across the last several -- the SAME 1-3 edges logged, at the SAME
point, every time, confirming this is not host contention or bad luck
but a deterministic per-call cost.

SUGGESTION: cache the per-file git-log walk `tdd_order_violations`
does across edges that target the SAME file within one land's scoped
set (T-3057's own scoping already groups edges; today each edge
re-walks its target file's full history independently even when N
edges share one file) -- this land's own case (2+ edges against the
same `src/frob/gates/__init__.py`) would have amortized to one walk.
Given TDD001 is already WARN-only and explicitly deferred to "a later
ticket's decision" to ever block a land, a bounded per-land time
budget (skip remaining edges and log a truncation notice past N
seconds/edges) would also make it safe against exactly this shape
without waiting for the caching fix.

ACCEPTANCE: a land whose diff touches 100+ frob:tests edges against a
handful of large-history files completes TDD001 in well under 595s,
measured against this same T-3586 diff (or an equivalent fixture) once
this ticket's fix lands.
