---
id: T-3032
title: Extract the graph concerns tickets shares with strata into the shared kernel,
  incrementally, one concern per land
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-4656
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/_hierarchy.py
- src/frob/gates/_milestone.py
- src/frob/tickets/_evidence.py
- tests/unit/test_graph_hierarchy.py
- docs/design/ticket-strata-shared-graph-inventory.md
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/_hierarchy.py
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/gates/_milestone.py
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/test_graph_hierarchy.py
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/design/ticket-strata-shared-graph-inventory.md
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/graph.md
  reason: 'T-3032: extract the duplicated parent/child descendants-BFS walk (frob.gates._milestone._descendants_of
    / frob.tickets._evidence._open_descendant_ids) into one shared frob.graph helper,
    plus the required per-concern inventory doc'
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: parent
  old_value: null
  new_value: T-4656
  reason: 'kernel-decoupling epic T-4651: rederive the frob kernel behind enforced
    module boundaries; this ticket already states the right work for this concern
    and is adopted as a child rather than duplicated'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: backlog
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.535.0
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-08-26, and it SUPERSEDES the "migrate tickets last" plan in
T-3004 section 9. That plan was a wholesale migration deferred to the end
because the ledger is the most contended machinery in the repo. The owner's
approach is better and is adopted instead:

  Find what `frob.tickets` has that strata ALSO needs, EXTRACT that to a shared
  kernel, build BOTH tickets and strata on it, and leave the dissimilar parts in
  tickets. The ticket refactor then happens INCREMENTALLY, one extraction at a
  time, with tickets' own regression tests as the safety net for each step.

MEASURED (2026-08-26) -- the shared surface is real and it is spread out. Count
of graph-shaped references (`parent`, `blocked_by`, `children`, `ancestor`,
`closure`, `cycle`, `graph`) per module:

    src/frob/tickets/_setters.py    81
    src/frob/tickets/_models.py     64
    src/frob/tickets/_doable.py     32
    src/frob/tickets/_store.py      28
    src/frob/tickets/_evidence.py   16
    src/frob/tickets/_scope.py       4

The tickets package is 41 files; the largest are `_land.py` (6,351 lines),
`_leases.py` (3,325), `_models.py` (2,907), `_store.py` (2,445).

`strata-core::graph` (landed T-3005, `0e4b42f38`) already provides the generic
half: typed nodes, typed edges, caller-supplied `GraphSchema`, construction-time
refusals, closure/reachability/cycle queries. So this is not "design a kernel" --
it is "identify what tickets duplicates of that kernel, and stop duplicating it".

LIKELY SHARED (verify each; do not assume):
  - parent/child hierarchy and ancestor walks
  - blocked_by edges and their transitive resolution
  - cycle detection over those edges
  - reachability / "what is doable" closure
  - typed-id identity and dangling-reference refusal

LIKELY TICKET-SPECIFIC (should STAY in tickets):
  - the state machine (queued/planned/in-progress/done/dropped) and its legal
    transitions
  - leases and worktree ownership
  - the land pipeline (squash, merge zones, LAND-PROOF, release artifacts)
  - evidence binding to pytest node ids
  - scope globs and lease conflicts

METHOD -- INCREMENTAL, one extraction per land:
  1. Pick ONE shared concern. Smallest first; `_doable`'s blocked_by closure or
     the parent/ancestor walk are good candidates.
  2. Prove tickets' existing regression tests cover its CURRENT behaviour BEFORE
     touching it. If coverage is thin, ADD tests first -- that is the safety net
     the whole approach depends on, and this repo enforces test-first for bug
     fixes already (BUG002) so the discipline is not new.
  3. Extract to the shared kernel, reroute tickets onto it, verify the
     regression tests still pass unchanged.
  4. Land. Then repeat.
  DO NOT extract several concerns in one land. The value of this approach is
  that each step is individually revertible; a multi-concern land throws that
  away.

CONSTRAINTS:
  - Ticket behaviour must not change. This is a refactor. Any behaviour
    difference is a bug, not an improvement, and must be reported rather than
    accepted.
  - The ledger is the most contended machinery in the repo -- on 2026-08-26 it
    produced a state=done with zero code on main, tip-drift refusals, a
    DirtyMain deadlock, a quarantine deadlock needing five land attempts, and
    multiple timeouts. Every extraction lands separately and small for that
    reason.
  - Where behaviour LOOKS shared but differs subtly, keep them separate and say
    why. A forced abstraction over two subtly-different semantics is worse than
    two implementations -- this repo has recorded that lesson already.

ACCEPTANCE
- A per-concern inventory: for each of the six modules above, which graph-shaped
  concerns are genuinely shared with strata and which are ticket-specific, with
  reasoning.
- At least one concern extracted end-to-end, with tickets rerouted onto the
  shared kernel and its regression tests passing unchanged.
- Evidence that the regression coverage for the extracted concern existed (or
  was added) BEFORE the extraction.
- The remaining concerns filed as individual follow-up tickets, one per
  extraction, so the increments stay small.
