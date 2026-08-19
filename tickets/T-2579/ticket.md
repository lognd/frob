---
id: T-2579
title: 'M4b: MILE004 gate for multiple runs-last tickets in one milestone'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: high
blocked_by:
- T-2574
parent: T-2573
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_milestone.py
- src/frob/gates/__init__.py
- src/frob/tickets/_models.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: register MILE004 in _KNOWN_GATE_RULES so frob:waive MILE004 binds, per coordinator
    instruction
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MILE004 (ERROR): reconcile MULTIPLE runs-last tickets sharing one
milestone. This is a directly requested design; do not relitigate, but
verify the code premise before building (already done, see below).

Verified premise (2026-08-18): `_other_open_tickets` in
src/frob/tickets/_doable.py already EXCLUDES fellow runs-last tickets
from its open-ticket count (`t.runs_last` check at line 67), so two
runs-last tickets never mutually deadlock. KEEP that carve-out --
removing it is a mutual deadlock, and this ticket must not touch it.

The gap: runs-last tickets do not wait for each other today, so "last"
really means "the last COHORT, in parallel", and nothing detects when
two of them actually needed ordering. Concrete instance: T-1614 audits
every `frob:waive` for cop-outs. If another runs-last ticket in the same
milestone adds or retargets waivers, the audit races the thing it
audits and silently produces a stale verdict.

MILE004 (ERROR): when two or more runs-last tickets share a milestone,
they must be EITHER ordered by a `blocked_by` edge, OR explicitly
declared parallel-safe with a reason. Ambiguity is a build failure, not
a race. The parallel-safe declaration mechanism needs a home -- follow
the existing `frob:waive`-style reason-carrying declaration shape used
elsewhere in this codebase rather than inventing a new one; do not use
`frob:waive MILE004` itself for this (that suppresses the finding
without recording WHY it is actually safe in a structured, queryable
way -- this needs its own declared-parallel-safe field/flag, not a
waiver).

Rejected alternative (recorded so it is not re-proposed): making
`runs_last` an integer RANK instead of a bool. Ranks are a made-up
global scale, and two tickets at equal rank recreate the identical
problem while looking decided.

Positive controls, both directions:
- two unordered runs-last tickets in one milestone: MILE004 FIRES.
- the same two with a blocked_by edge between them: does NOT fire.
- the same two declared parallel-safe: does NOT fire.
- a single runs-last ticket alone in a milestone: never fires.

Depends on M1 (T-2574, field must exist). Does not depend on M3/M4 --
MILE004 is a static ledger check, independent of doable ordering
mechanics.
