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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
