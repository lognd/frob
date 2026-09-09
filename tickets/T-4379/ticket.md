---
id: T-4379
title: T-2104's IN_PROGRESS scope-narrowing self-heal releases blocked_by on ANY empty-scope
  ticket, not just narrowed scope
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_doable.py
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
found while measuring T-3852's addendum FACT 2 (a container ticket's dependents became doable once the container was merely STARTED, not done). Root cause confirmed by direct code read: _open_blockers (src/frob/tickets/_doable.py) drops an IN_PROGRESS blocker's edge when scope_overlap_globs(ticket.scope, lease_scope) is None (T-2104's self-heal for a blocker whose scope narrowed mid-work, T-2076's own incident). scope_overlap_globs returns None unconditionally whenever either side's glob list is empty (src/frob/tickets/_models.py::scope_overlap_globs -- the inner loop never executes over an empty list). A container ticket (no_scope_declared=True, scope=()) therefore has an EMPTY lease scope from the moment it starts, so scope_overlap_globs(anything, ()) is always None -- its blocked_by edge is dropped for EVERY dependent the instant it transitions to IN_PROGRESS, regardless of whether its actual (rollup) work is done. This is a different bug from a genuine scope-narrowing self-heal: T-2104 was designed for a blocker whose scope shrank DURING work to no longer collide with a specific dependent, not for a blocker that never had scope to begin with. VERDICT (per T-3852's explicit instruction to measure and report, not fix under that ticket): this is UNINTENDED. A container's dependents should wait for the container to actually DONE-close (now reachable without pytest evidence via T-3852's rollup path), not for it to merely start. Fix direction: _open_blockers should not apply the scope-narrowing self-heal when the blocker's OWN declared scope was already empty at block-time (no genuine narrowing occurred, since there was nothing to narrow from) -- distinguish 'scope shrank' from 'scope was never declared'.