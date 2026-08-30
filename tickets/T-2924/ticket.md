---
id: T-2924
title: Scope the inline land check_gates spawn to the merge delta for non-rapid profiles
state: queued
kind: feature
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_verify.py
- tests/unit/app/ticket_runner/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'ticket text: scope named files plus tests for the new --only selection'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'ticket text: scope named files plus tests for the new --only selection'
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/app/ticket_runner/**
  reason: 'ticket text: scope named files plus tests for the new --only selection'
  actor: logan
  at: '2026-08-25'
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: T-2913 removed the inline gate-count claim re-verification under rapid and
    nothing deferred restores that property; scoping the spawn to the merge delta
    is the path that makes it cheap enough to run again, so this is the restoration
    ticket, not an optimization
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
labels:
- restores-dropped-guard
anchor: false
anchor_reason: null
land_commit: null
---
T-2913 removed the redundant INLINE `check_gates`/`check_gate_findings`
spawn from rapid lands by deferring to the existing post-land sweep
queue. It did not attempt option (a) from the coordinator's brief:
scoping that same spawn to the merge delta (an `--only <families>`
selection derived from the files actually touched between
`pre_land_tip` and the squashed tree) for FORTRESS/STANDARD profile
lands, which still pay the full inline cost unconditionally.

`_verify.py`'s own T-1344/T-2053 investigation already names this as
the one change that could turn the gate cache's structural near-always
-miss (on a freshly-merged tree) into a near-always-hit, and names
exactly what it needs: land's own diff threaded into
`_shared_check_spawn_fn`'s closure construction, which currently only
takes `(root, ticket_id)`. That construction call lives in
`_land_cmd.py` (`_land_core_invoke`), which a concurrent ticket
(T-2609) held an exclusive scope lease on for T-2913's entire session --
not a design obstacle, purely a scheduling one.

Scope: src/frob/app/ticket_runner/_land_cmd.py,
src/frob/app/ticket_runner/_verify.py (both already need touching for
the diff-threading), tests covering the new `--only` selection.

## Failure log
- 2026-08-25 attempt 2: no safe --only merge-delta scoping exists; it drops ToolResult coverage the T-0754 divergence check relies on -- needs owner decision, see Done report
- 2026-08-30 attempt 3: structurally undoable as scoped, confirmed a third time: this ticket's own attempt 2 (2026-08-25) found no safe --only merge-delta scoping exists ('drops ToolResult coverage the T-0754 divergence check relies on'). That conclusion is now independently baked into current main's own code: src/frob/app/ticket_runner/_verify.py lines 908-925 (the _shared_check_spawn_fn docstring's T-1344/T-2053 investigation) states explicitly '--only/family-skipping is NOT safe' and '--delta does NOT reduce wall-clock at all'. Forcing a --only merge-delta selection here would silently narrow the T-0754 divergence check's own coverage. T-3054 (landed, src/frob/tickets/_land.py::_land_should_skip_inline_claims_reverify / _land_deadline_cannot_afford_inline_claims_reverify) already extended the only viable alternative mechanism -- skip the inline spawn entirely (never scope it) -- from rapid-only to any profile with a declared FROB_LAND_DEADLINE_S too small to afford it. T-2924's literal ask (merge-delta --only scoping) remains unsafe and should not be forced; no owner decision has reversed the T-1344/T-2053 conclusion.
