---
id: T-4427
title: set_sprint/set_milestone must record a TriageChangeEntry with the assignment
  date
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- tests/test_tickets_triage_dates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/test_tickets_priority.py
  reason: T-4424 holds a live lease on test_tickets_priority.py; use a new dedicated
    test file to avoid the collision
  actor: logan
  at: '2026-09-11'
- op: add
  glob: tests/test_tickets_triage_dates.py
  reason: T-4424 holds a live lease on test_tickets_priority.py; use a new dedicated
    test file to avoid the collision
  actor: logan
  at: '2026-09-11'
body_changes:
- mode: set
  reason: full requirements for the TriageChangeEntry recording fast-follow
  actor: logan
  at: '2026-09-11'
  old_length: 0
  new_length: 3301
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FAST-FOLLOW from T-4424 (TICK004 sprint/milestone triage). T-4424's fix
reads a sprint/milestone assignment date from `t.triage_changes` (the most
recent `TriageChangeEntry` whose `field` is `"sprint"`/`"milestone"`) to
restart the rot clock at triage time instead of `created`. It fails safe
to "not rotting" when no such entry exists -- which is EVERY currently-
sprinted ticket in the live ledger today, because `set_sprint`/
`set_milestone` (src/frob/tickets/_setters.py) call `_set_ticket_field`
with `reason=None`, so `_set_ticket_field`'s own `if reason is not None`
branch never appends a `TriageChangeEntry` for either field.

REQUIRED BEHAVIOR
1. `set_sprint(root, ticket_id, sprint)` records a `TriageChangeEntry`
   (`field="sprint"`, old/new value, actor, `at=date.today()`) exactly the
   way `set_priority`/`set_kind`/`set_component`/`set_tier` already do via
   `_set_ticket_field`'s `reason` parameter -- either add a `reason`
   parameter to `set_sprint`'s own signature (mirroring the other four
   setters, which is the more consistent shape) or pass a fixed internal
   reason string if a `sprint assign` CLI call site truly has none to
   give; read `frob ticket sprint assign`'s CLI surface (wherever it calls
   `set_sprint`) to decide which and keep the CLI ergonomics sane -- do
   not silently drop a caller-supplied reason if one already exists at
   the CLI layer.
2. `set_milestone` (same module) gets the identical treatment -- it must
   also record a `TriageChangeEntry` (`field="milestone"`) when the
   milestone is set, for the same T-4424 read path
   (`_tick004_triage_date` already checks both fields' entries).
3. A no-op re-assignment (same value) still records an entry when a
   reason is given, matching `_set_ticket_field`'s existing "no-op write
   still appends an entry when reason is given" contract (T-2353) --
   do not special-case sprint/milestone to skip this.
4. Existing already-sprinted tickets in the ledger (no historical entry)
   are NOT backfilled by this ticket -- out of scope, a data migration
   concern, not a code fix. They simply stay fail-safe-quiet under
   T-4424's own fix until someone re-runs `sprint assign` on them (or a
   separate migration ticket is filed if that is unacceptable).

TESTS REQUIRED
- `set_sprint` on a ticket with no prior sprint records a `TriageChangeEntry`
  with `field="sprint"`, correct old/new values, and `at` equal to today.
- `set_milestone` records the equivalent entry with `field="milestone"`.
- A no-op re-assignment (same sprint value) with a reason still appends an
  entry (does not silently no-op the audit trail).
- `_tick004_triage_date` (src/frob/gates/_tickets_gate.py, already landed
  by T-4424) picks up the newly-recorded date end-to-end: assign a sprint
  via `set_sprint`, then run `_tick004_queue_rot` on a ticket that is past
  its created-date threshold but freshly sprinted -- confirm it is now
  quiet via the REAL recorded date, not just the synthetic
  `TriageChangeEntry` construction T-4424's own tests used.

SCOPE: src/frob/tickets/_setters.py plus its test file
(tests/test_tickets_priority.py, where TestSetPriority-style setter tests
already live). Do not touch TICK004 gate code itself (T-4424's own scope,
already landed) beyond the one integration test above.
